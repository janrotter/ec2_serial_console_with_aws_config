from pathlib import Path

import git
from aws_cdk import BundlingOptions, DockerImage, Stack
from aws_cdk import aws_cloudformation as cloudformation
from aws_cdk import aws_s3_assets as assets
from constructs import Construct


def get_repo_root():
    repo = git.Repo(__file__, search_parent_directories=True)
    if not repo.working_tree_dir:
        raise RuntimeError("Cannot find the Git root dir")
    return Path(repo.working_tree_dir)


CLOUDFORMATION_EXTENSIONS_DIR = get_repo_root() / "cdk" / "cloudformation_extensions"


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

        cfn_resource_version = cloudformation.CfnResourceVersion(
            self,
            "Ec2SerialConsoleAccessCfnResourceVersion",
            schema_handler_package=bundle.s3_object_url,
            type_name="AWSCustom::EC2::SerialConsoleAccess",
        )

        cloudformation.CfnResourceDefaultVersion(
            self,
            "Ec2SerialConsoleAccessCfnResourceDefaultVersion",
            type_version_arn=cfn_resource_version.attr_arn,
        )
