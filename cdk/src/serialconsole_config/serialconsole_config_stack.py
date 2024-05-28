from pathlib import Path

import git
from aws_cdk import BundlingOptions, CustomResource, DockerImage, Duration, Stack
from aws_cdk import aws_cloudformation as cloudformation
from aws_cdk import aws_config
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_s3_assets as assets
from aws_cdk import aws_sqs as sqs
from constructs import Construct
from git import config


def get_repo_root():
    repo = git.Repo(__file__, search_parent_directories=True)
    if not repo.working_tree_dir:
        raise RuntimeError("Cannot find the Git root dir")
    return Path(repo.working_tree_dir)


CDK_ROOT = get_repo_root() / "cdk"
CLOUDFORMATION_EXTENSIONS_DIR = CDK_ROOT / "cloudformation_extensions"


class SerialconsoleConfigStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ec2_serial_console_access_dir = str(
            CLOUDFORMATION_EXTENSIONS_DIR / "ec2_serial_console_access"
        )

        bundle = assets.Asset(
            self,
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
            self,
            "Ec2SerialConsoleAccessCfnResourceVersion",
            schema_handler_package=bundle.s3_object_url,
            type_name=TYPE_NAME,
        )

        resource_default_version = cloudformation.CfnResourceDefaultVersion(
            self,
            "Ec2SerialConsoleAccessCfnResourceDefaultVersion",
            type_version_arn=cfn_resource_version.attr_arn,
        )

        dependencies_layer = lambda_.LayerVersion(
            self,
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

        config_updater_lambda = lambda_.Function(
            self,
            "UpdateEc2SerialConsoleAccessStateInAwsConfigLambda",
            function_name="updateEc2SerialConsoleAccessStateInAwsConfig",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="ec2_serial_console.update_config_state",
            code=lambda_.Code.from_asset(str(CDK_ROOT / "src" / "lambdas")),
            layers=[dependencies_layer],
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
            self,
            "DisableSerialConsoleLambda",
            function_name="disableSerialConsoleLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="ec2_serial_console.disable_serial_console",
            code=lambda_.Code.from_asset(str(CDK_ROOT / "src" / "lambdas")),
            layers=[dependencies_layer],
            timeout=Duration.seconds(15),
        )

        disable_serial_console_lambda.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["ec2:DisableSerialConsoleAccess"],
            )
        )

        dlq = sqs.Queue(self, "DLQ")

        rule = events.Rule(
            self,
            "UpdateEc2SerialConsoleStatusRule",
            event_pattern=events.EventPattern(
                source=["aws.ec2"], detail={"eventName": ["EnableSerialConsoleAccess"]}
            ),
        )
        rule.add_target(
            targets.LambdaFunction(
                config_updater_lambda,
                dead_letter_queue=dlq,
                max_event_age=Duration.hours(1),
                retry_attempts=2,
            )
        )

        cr = CustomResource(
            self,
            "UpdateTheConfigStateCR",
            resource_type="Custom::UpdateAwsConfigState",
            service_token=config_updater_lambda.function_arn,
        )
        cr.node.add_dependency(resource_default_version)
