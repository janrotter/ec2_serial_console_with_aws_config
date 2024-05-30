# AWS CDK with Python

A word of warning - AWS CDK is noticeably slower with its Python implementation
than the native TypeScript one. Simply listing the stacks takes about 15
seconds, unit tests take about 30 seconds. Please be patient.

## Stacks

- SerialconsoleConfigStack - a stack that sets up AWS Config (together with
  accompanying resources) to ensure that the EC2 Serial Console is disabled.
  CloudTrail and AWS Config have to be configured prior to deployment.

## Testing

Snapshot tests are available, you can run them with:
```
make test
```
and update the snapshots with:
```
make update_test_snapshots
```
