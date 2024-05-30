import aws_cdk as core
import aws_cdk.assertions as assertions

from serialconsole_config.serialconsole_config_stack import SerialconsoleConfigStack


def test_serial_console_config_stack_matches_the_snapshot(snapshot):
    app = core.App()
    stack = SerialconsoleConfigStack(app, "serialconsole-config")
    template = assertions.Template.from_stack(stack)
    template_json = template.to_json()
    template_json["Resources"][
        "ResourcesEc2SerialConsoleAccessCfnResourceVersionF78104F2"
    ]["Properties"]["SchemaHandlerPackage"] = "placeholder"
    assert template_json == snapshot
