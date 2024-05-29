import boto3
from crhelper import CfnResource

helper = CfnResource()


@helper.create
def create(event, context):
    cloudtrail_client = boto3.client("cloudtrail")

    response = cloudtrail_client.describe_trails()
    trails = response.get("trailList", {})
    if not trails:
        raise ValueError("It seems that CloudTrail has no trails.")


def check_aws_cloudtrail_has_trails(event, context):
    helper(event, context)
