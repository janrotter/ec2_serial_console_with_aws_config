import aws_cdk as core
import aws_cdk.assertions as assertions

from serialconsole_config.serialconsole_config_stack import SerialconsoleConfigStack

# example tests. To run these tests, uncomment this file along with the example
# resource in serialconsole_config/serialconsole_config_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = SerialconsoleConfigStack(app, "serialconsole-config")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
