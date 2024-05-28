import json

import boto3
import requests

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
    data = {
        "Status": "SUCCESS",
        "Reason": f"You can check the execution logs here: {context.log_stream_name}",
        "StackId": event.get("StackId"),
        "RequestId": event.get("RequestId"),
        "LogicalResourceId": event.get("LogicalResourceId"),
        "PhysicalResourceId": event.get("StackId"),
    }

    try:
        record_ec2_serial_console_status_to_aws_config()
        if "StackId" in event:
            response = requests.put(event["ResponseURL"], data=json.dumps(data))
            response.raise_for_status()
    except Exception as e:
        if "StackId" in event:
            data["Status"] = "FAILED"
            response = requests.put(event["ResponseURL"], data=json.dumps(data))
            response.raise_for_status()
        else:
            raise


def disable_serial_console(event, context):
    ec2_client = boto3.client("ec2")

    result = ec2_client.disable_serial_console_access()
    if result["SerialConsoleAccessEnabled"] != False:
        raise RuntimeError(
            "Something went terribly wrong, the serial console is enabled after explicitly disabling it!"
        )
