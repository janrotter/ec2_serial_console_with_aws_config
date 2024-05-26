# AWSCustom::EC2::SerialConsoleAccess

This is a resource type that can be used to keep track of the EC2 Serial
Console Access setting with AWS Config.

As there are no handlers implemented, the resource cannot be instantiated by
the CloudFormation nor its supported by the Cloud Control.

## Building

It is automatically packaged and uploaded to S3 by the CDK app. This approach
should be preferred, as the build will run in the bundling container. In case
you would like to upload it manually anyway, please run:
```
cfn submit --set-default
```

## Contract testing

Currently there are no handlers to test, so this can be skipped. In case this
resource is extended to include them, you can run the contract tests by:
- making sure that you rebuild the package with `cfn package`, as SAM will look
  for the code in the `build/` folder.
- running the local version of the handlers with `sam local start-lambda`
- running the contract tests themselves with `cfn test`
