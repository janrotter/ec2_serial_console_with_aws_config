from pathlib import Path

import git
import jsii
from aws_cdk import (
    Aspects,
    BundlingOptions,
    CustomResource,
    DockerImage,
    Duration,
    IAspect,
    Stack,
)
from aws_cdk import aws_cloudformation as cloudformation
from aws_cdk import aws_config
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3_assets as assets
from aws_cdk import aws_sqs as sqs
from constructs import Construct, DependencyGroup
from git import config


def get_repo_root():
    repo = git.Repo(__file__, search_parent_directories=True)
    if not repo.working_tree_dir:
        raise RuntimeError("Cannot find the Git root dir")
    return Path(repo.working_tree_dir)


CDK_ROOT = get_repo_root() / "cdk"
CLOUDFORMATION_EXTENSIONS_DIR = CDK_ROOT / "cloudformation_extensions"


@jsii.implements(IAspect)
class DependsOnAspect:
    def __init__(self, dependency):
        self.dependency = dependency
        if isinstance(dependency, CustomResource):
            self.dependency = dependency.node.default_child

    def visit(self, node):
        if not isinstance(node, Stack) and hasattr(node, "add_dependency"):
            node.add_dependency(self.dependency)


class SerialconsoleConfigStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.prerequisites = Construct(self, "Prerequisites")
        self.resources = Construct(self, "Resources")
        self.finalizers = Construct(self, "Finalizers")

        self.dependencies_layer = lambda_.LayerVersion(
            self.prerequisites,
            "DependenciesLambdaLayer",
            code=lambda_.Code.from_asset(
                str(CDK_ROOT / "src" / "lambdas"),
                bundling=BundlingOptions(
                    image=DockerImage.from_registry(
                        "python:3.12@sha256:3966b81808d864099f802080d897cef36c01550472ab3955fdd716d1c665acd6"
                    ),
                    command=[
                        "bash",
                        "-c",
                        "pip install -r requirements.txt --target /asset-output/python/",
                    ],
                ),
            ),
        )

        ec2_serial_console_access_dir = str(
            CLOUDFORMATION_EXTENSIONS_DIR / "ec2_serial_console_access"
        )

        bundle = assets.Asset(
            self.resources,
            "Ec2SerialConsoleAccessExtensionBundle",
            path=ec2_serial_console_access_dir,
            bundling=BundlingOptions(
                image=DockerImage.from_build(ec2_serial_console_access_dir),
                command=[
                    "bash",
                    "-c",
                    "cfn package && mv awscustom-ec2-serialconsoleaccess.zip /asset-output/",
                ],
            ),
        )

        TYPE_NAME = "AWSCustom::EC2::SerialConsoleAccess"
        cfn_resource_version = cloudformation.CfnResourceVersion(
            self.resources,
            "Ec2SerialConsoleAccessCfnResourceVersion",
            schema_handler_package=bundle.s3_object_url,
            type_name=TYPE_NAME,
        )

        resource_default_version = cloudformation.CfnResourceDefaultVersion(
            self.resources,
            "Ec2SerialConsoleAccessCfnResourceDefaultVersion",
            type_version_arn=cfn_resource_version.attr_arn,
        )

        config_updater_lambda = lambda_.Function(
            self.resources,
            "UpdateEc2SerialConsoleAccessStateInAwsConfigLambda",
            function_name="updateEc2SerialConsoleAccessStateInAwsConfig",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="ec2_serial_console.update_config_state",
            code=lambda_.Code.from_asset(str(CDK_ROOT / "src" / "lambdas")),
            layers=[self.dependencies_layer],
            timeout=Duration.seconds(30),
        )
        config_updater_lambda.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=[
                    "cloudformation:DescribeType",
                    "config:PutResourceConfig",
                    "ec2:GetSerialConsoleAccessStatus",
                ],
            )
        )

        disable_serial_console_lambda = lambda_.Function(
            self.resources,
            "DisableSerialConsoleLambda",
            function_name="disableSerialConsoleLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="ec2_serial_console.disable_serial_console",
            code=lambda_.Code.from_asset(str(CDK_ROOT / "src" / "lambdas")),
            layers=[self.dependencies_layer],
            timeout=Duration.seconds(15),
        )

        disable_serial_console_lambda.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["ec2:DisableSerialConsoleAccess"],
            )
        )

        dlq = sqs.Queue(self.resources, "DLQ")

        rule = events.Rule(
            self.resources,
            "UpdateEc2SerialConsoleStatusRule",
            event_pattern=events.EventPattern(
                source=["aws.ec2"], detail={"eventName": ["EnableSerialConsoleAccess"]}
            ),
            schedule=events.Schedule.rate(Duration.days(1)),
        )
        rule.add_target(
            targets.LambdaFunction(
                config_updater_lambda,
                dead_letter_queue=dlq,
                max_event_age=Duration.hours(1),
                retry_attempts=2,
            )
        )

        # Prerequisites
        check_config_enabled = lambda_.Function(
            self.prerequisites,
            "CheckAwsConfigEnabledLambda",
            description="This function is used to create a custom "
            "CloudFormation resource that upon its creation makes "
            "sure that AWS Config recorder is present. This allows "
            "us to avoid creating resources that depend on it "
            "and could get stuck upon creation.",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="cfn_custom_resources.check_aws_config.check_aws_config_recorder_present",
            code=lambda_.Code.from_asset(str(CDK_ROOT / "src" / "lambdas")),
            layers=[self.dependencies_layer],
            timeout=Duration.seconds(15),
        )

        check_config_enabled.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["config:DescribeConfigurationRecorders"],
            )
        )
        check_config_cr = CustomResource(
            self.prerequisites,
            "CheckAwsConfigCR",
            resource_type="Custom::CheckAwsConfigRecorderPresence",
            service_token=check_config_enabled.function_arn,
        )

        check_cloudtrail_enabled = lambda_.Function(
            self.prerequisites,
            "CheckCloudTrailEnabled",
            description="This function is used to create a custom "
            "CloudFormation resource that upon its creation makes "
            "sure that AWS CloudTrail trail is present. This allows "
            "us to avoid creating resources that depend on it "
            "and could get stuck upon creation.",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="cfn_custom_resources.check_aws_cloudtrail.check_aws_cloudtrail_has_trails",
            code=lambda_.Code.from_asset(str(CDK_ROOT / "src" / "lambdas")),
            layers=[self.dependencies_layer],
            timeout=Duration.seconds(15),
        )

        check_cloudtrail_enabled.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["cloudtrail:DescribeTrails"],
            )
        )
        check_cloudtrail_cr = CustomResource(
            self.prerequisites,
            "CheckCloudTrailCR",
            resource_type="Custom::CheckAwsCloudTrailTrailsPresence",
            service_token=check_cloudtrail_enabled.function_arn,
        )

        Aspects.of(self.resources).add(DependsOnAspect(check_config_cr))
        Aspects.of(self.resources).add(DependsOnAspect(check_cloudtrail_cr))

        self.add_finalizers(dependencies=[resource_default_version])

    def add_finalizers(self, dependencies):
        cr_lambda = lambda_.Function(
            self.finalizers,
            "UpdateEc2SerialConsoleAccessStateInAwsConfigLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="cfn_custom_resources.update_ec2_serial_console_status."
            "update_ec2_serial_console_status_in_aws_config",
            code=lambda_.Code.from_asset(str(CDK_ROOT / "src" / "lambdas")),
            layers=[self.dependencies_layer],
            timeout=Duration.seconds(30),
        )
        cr_lambda.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=[
                    "cloudformation:DescribeType",
                    "config:PutResourceConfig",
                    "ec2:GetSerialConsoleAccessStatus",
                ],
            )
        )
        cr = CustomResource(
            self.finalizers,
            "UpdateTheConfigStateCR",
            resource_type="Custom::UpdateAwsConfigState",
            service_token=cr_lambda.function_arn,
        )

        for d in dependencies:
            cr.node.add_dependency(d)
