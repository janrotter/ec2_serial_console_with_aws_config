# This container is used to bundle the CloudFormation Extension package by the CDK

FROM python:3.12@sha256:3966b81808d864099f802080d897cef36c01550472ab3955fdd716d1c665acd6


WORKDIR /opt/cloudformation_extensions
ADD bundle-requirements.txt .
RUN pip install -r bundle-requirements.txt

CMD bash
