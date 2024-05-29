import json

import boto3

TYPE_NAME = "AWSCustom::EC2::SerialConsoleAccess"


def record_ec2_serial_console_status_to_aws_config():
    cloudformation_client = boto3.client("cloudformation")
    schema_version = cloudformation_client.describe_type(
        Type="RESOURCE", TypeName=TYPE_NAME
    )["DefaultVersionId"]

    region = cloudformation_client.meta.region_name
    serial_console_allowed = boto3.client("ec2").get_serial_console_access_status()[
        "SerialConsoleAccessEnabled"
    ]

    model_json = json.dumps({"Region": region, "Allowed": serial_console_allowed})

    config_client = boto3.client("config")
    config_client.put_resource_config(
        ResourceType=TYPE_NAME,
        SchemaVersionId=schema_version,
        ResourceId=region,
        ResourceName=region,
        Configuration=model_json,
    )


def update_config_state(event, context):
    record_ec2_serial_console_status_to_aws_config()


def disable_serial_console(event, context):
    ec2_client = boto3.client("ec2")

    result = ec2_client.disable_serial_console_access()
    if result["SerialConsoleAccessEnabled"] != False:
        raise RuntimeError(
            "Something went terribly wrong, the serial console is enabled after explicitly disabling it!"
        )
