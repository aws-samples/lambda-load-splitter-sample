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

# This file provides unit tests for the "extract_event_from_queue_message()" method
# which allows safely digging into an arbitrarily nested structure of python lists and
# dictionaries (as one might have after converting JSON to python lists/dicts)
#
# To run this test, execute it from the parent directory where your lambda code under test resides:
#   python -m pytest tests/*.py
#
# References:
#   https://docs.pytest.org/en/stable/index.html

import json
import sys

import pytest

sys.path.append("load_splitter_lambda/code") # needed for aws and pytest
from event_queue import extract_event_from_queue_message


def generate_sqs_event():
    # -*- coding: utf-8 -*-
    """
    This method generates the essential parts of an example SQS message that a Lambda
    would receive if it were hooked up to an SQS queue. In this example, the "body"
    field contains a string that happens to also be string-encoded JSON.
    """
    return \
        {
            "Records": [
                {
                    "body":
                        "{'detail': {'eventSource': 'ec2.amazonaws.com', 'eventName': 'CreateTags', 'awsRegion': 'us-west-2', 'requestParameters': {'resourcesSet': {'items': [{'resourceId': 'i-00000000000000000'}]}, 'tagSet': {'items': [{'key': 'tag-key-1', 'value': 'tag-value-1'}]}}}}",
                    "eventSource": "aws:sqs"
                }
            ]
        }

def generate_sqs_event_without_event_source():
    tmp = generate_sqs_event()
    # remove the "eventSource" from the JSON
    del tmp["Records"][0]["eventSource"]
    return tmp

def generate_sqs_event_without_body():
    tmp = generate_sqs_event()
    # remove the "eventSource" from the JSON
    del tmp["Records"][0]["body"]
    return tmp

def generate_sqs_event_with_bad_body_json():
    tmp = generate_sqs_event()
    # remove the "eventSource" from the JSON
    tmp["Records"][0]["body"] = "some non-json parsable garbage"
    return tmp

def generate_ec2_event():
    tmp = generate_sqs_event()
    # change the JSON so the message appears to be from EC2, not SQS
    tmp["Records"][0]["eventSource"] = "aws:ec2"
    return tmp

def generate_create_tags_event():
    # -*- coding: utf-8 -*-
    """
    This method generates the JSON that is embedded in the "body" field
    that is output by the generate_sample_sqs_event() method.
    """
    return \
        {
            "detail": {
                "eventSource": "ec2.amazonaws.com",
                "eventName": "CreateTags",
                "awsRegion": "us-west-2",
                "requestParameters": {
                    "resourcesSet": {
                        "items": [ { "resourceId": "i-00000000000000000" } ]
                    },
                    "tagSet": {
                        "items": [
                            { "key": "tag-key-1", "value": "tag-value-1" } ]
                    }
                },
            }
        }

class TestEventQueue():
    def test_sqs_event(self):
        input = generate_sqs_event()
        expected_output = generate_create_tags_event()
        res = extract_event_from_queue_message(input)
        assert(res == expected_output)
    def test_ec2_event(self):
        input = generate_ec2_event()
        res = extract_event_from_queue_message(input)
        assert(res == None)
    def test_bad_sqs_event_source(self):
        input = generate_sqs_event_without_event_source()
        res = extract_event_from_queue_message(input)
        assert(res == None)
    def test_bad_sqs_body(self):
        input = generate_sqs_event_with_bad_body_json()
        with pytest.raises(json.JSONDecodeError):
            res = extract_event_from_queue_message(input)
    def test_bad_sqs_no_body(self):
        input = generate_sqs_event_without_body()
        res = extract_event_from_queue_message(input)
        assert(res == None)
