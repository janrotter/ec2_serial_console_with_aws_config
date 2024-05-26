# AWSCustom::EC2::SerialConsoleAccess

Controls the EC2 Serial Console Access region-wide setting

## Syntax

To declare this entity in your AWS CloudFormation template, use the following syntax:

### JSON

<pre>
{
    "Type" : "AWSCustom::EC2::SerialConsoleAccess",
    "Properties" : {
        "<a href="#allowed" title="Allowed">Allowed</a>" : <i>Boolean</i>
    }
}
</pre>

### YAML

<pre>
Type: AWSCustom::EC2::SerialConsoleAccess
Properties:
    <a href="#allowed" title="Allowed">Allowed</a>: <i>Boolean</i>
</pre>

## Properties

#### Allowed

Is the EC2 Serial Console access allowed?

_Required_: No

_Type_: Boolean

_Update requires_: [No interruption](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-cfn-updating-stacks-update-behaviors.html#update-no-interrupt)

## Return Values

### Ref

When you pass the logical ID of this resource to the intrinsic `Ref` function, Ref returns the Region.

### Fn::GetAtt

The `Fn::GetAtt` intrinsic function returns a value for a specified attribute of this type. The following are the available attributes and sample return values.

For more information about using the `Fn::GetAtt` intrinsic function, see [Fn::GetAtt](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/intrinsic-function-reference-getatt.html).

#### Region

The AWS region where the serial console access setting is configured
