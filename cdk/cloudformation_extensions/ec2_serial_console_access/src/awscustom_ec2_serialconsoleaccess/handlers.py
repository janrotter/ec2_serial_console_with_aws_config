import logging

from cloudformation_cli_python_lib import Resource

from .models import ResourceModel

LOG = logging.getLogger(__name__)
TYPE_NAME = "AWSCustom::EC2::SerialConsoleAccess"

resource = Resource(TYPE_NAME, ResourceModel)
test_entrypoint = resource.test_entrypoint
