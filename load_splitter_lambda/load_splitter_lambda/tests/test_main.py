#######################################################################################
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#######################################################################################

# To run this test, execute it from the parent directory where your lambda code under test resides:
#   python -m pytest tests
#
# References:
#   https://docs.pytest.org/en/stable/index.html
#   https://realpython.com/python-mock-library/
#

import json
import os
import sys

import boto3
import pytest
from mock import patch
from moto import mock_sqs

REGION_NAME = "us-west-1"
PREFIX      = "MY_PREFIX"

sys.path.append("load_splitter_lambda/code") # needed for aws and pytest
from main import lambda_handler


@pytest.fixture(scope="function")
def aws_credentials():
    os.environ["AWS_DEFAULT_REGION"] = REGION_NAME
    os.environ["QUEUE_NAME"]         = PREFIX

class TestData:
    def create_3_tags_event():
        return {
            "detail": {
                "eventSource": "ec2.amazonaws.com",
                "eventName": "CreateTags",
                "requestParameters": {
                    "resourcesSet": {
                        "items": [ { "resourceId": "i-00000000000000000" } ]
                    },
                    "tagSet": {
                        "items": [
                            { "key": "tag-key-1", "value": "tag-value-1" },
                            { "key": "tag-key-2", "value": "tag-value-2" },
                            { "key": "tag-key-3", "value": "tag-value-3" }  ] }
                },    }
        }
    def create_1_tag_event():
        return {
            "detail": {
                "eventSource": "ec2.amazonaws.com",
                "eventName": "CreateTags",
                "requestParameters": {
                    "resourcesSet": {
                        "items": [ { "resourceId": "i-00000000000000000" } ]
                    },
                    "tagSet": {
                        "items": [
                            { "key": "tag-key-1", "value": "tag-value-1" }  ] }
                },    }
        }


@mock_sqs
def test_lambda_handler_with_empty_event(aws_credentials):
    # TEST SETUP ---------------------------------------------------------------------------
    event = {}
    # RUN TEST -----------------------------------------------------------------------------
    from main import lambda_handler
    out = lambda_handler(event, {})
    # VALIDATE RESULTS ---------------------------------------------------------------------
    assert out == {
        "statusCode": 400,
        "count":      0,
        "body":       "invalid event argument"
    }, "Expecting lambda to return saying 'invalid event argument'"

@mock_sqs
@patch('time.sleep', return_value=None)
def test_lambda_handler_with_1_tag(aws_credentials):
    # TEST SETUP ---------------------------------------------------------------------------
    event = TestData.create_1_tag_event()
    # RUN TEST -----------------------------------------------------------------------------
    from main import lambda_handler
    out = lambda_handler(event, {})
    # VALIDATE RESULTS ---------------------------------------------------------------------
    assert out == {
        "statusCode": 200,
        "count":      1,
        "body":       "handled 1 tag"
    }, "Expecting lambda to return with count of '1' and body of 'handled 1 tag'"

@mock_sqs
def test_lambda_handler_with_3_tags(aws_credentials):
    # TEST SETUP ---------------------------------------------------------------------------
    COUNT = 3
    # mock an SQS queue with the right name
    queue = boto3.resource("sqs").create_queue(QueueName=os.environ["QUEUE_NAME"])
    event = TestData.create_3_tags_event()
    assert COUNT == len(event["detail"]["requestParameters"]["tagSet"]["items"]), f"Expecting input test data to have {COUNT} tags"
    # RUN TEST -----------------------------------------------------------------------------
    from main import lambda_handler
    out = lambda_handler(event, {})
    # VALIDATE RESULTS ---------------------------------------------------------------------
    assert out == {
        "statusCode": 202,
        "count":      COUNT,
        "body":       f"split '{COUNT}' tags into '{COUNT}' queued messages"
    }, f"Expecting lambda to return saying it split '{COUNT}' tags into '{COUNT}' queued messages"
    # read messages from the queue
    sqs_messages = queue.receive_messages(MaxNumberOfMessages=10)
    assert len(sqs_messages) == COUNT, "Expecting exactly one message in SQS"
    # validate the count of the number of tags in the message
    output_message = json.loads(sqs_messages[0].body)
    tag_count_after = len(output_message["detail"]["requestParameters"]["tagSet"]["items"])
    assert tag_count_after == 1, "Expecting just one tag in the output"
