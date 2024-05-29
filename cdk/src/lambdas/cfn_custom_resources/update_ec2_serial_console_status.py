import boto3
from crhelper import CfnResource
from ec2_serial_console import record_ec2_serial_console_status_to_aws_config

helper = CfnResource()


@helper.create
def create(event, context):
    record_ec2_serial_console_status_to_aws_config()


def update_ec2_serial_console_status_in_aws_config(event, context):
    helper(event, context)
