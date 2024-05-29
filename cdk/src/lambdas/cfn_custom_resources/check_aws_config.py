import boto3
from crhelper import CfnResource

helper = CfnResource()


@helper.create
def create(event, context):
    config_client = boto3.client("config")
    response = config_client.describe_configuration_recorders()

    recorders_status = response.get("ConfigurationRecorders", {})
    if not recorders_status:
        raise ValueError("There is no AWS Config configuration recorder configured.")


def check_aws_config_recorder_present(event, context):
    helper(event, context)
