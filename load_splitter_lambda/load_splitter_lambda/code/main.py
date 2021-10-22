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

import json
import logging
import sys
import time

import boto3
import botocore

sys.path.append("load_splitter_lambda/code") # needed for aws and pytest
from event_queue import extract_event_from_queue_message, queue_smaller_events

logger = logging.getLogger()

def process_one_tag(tag):
    logger.info(f"===> START processing tag '{tag['key']}'")
    # simulate some time-consuming work
    time.sleep(5)
    logger.info(f"===> DONE processing tag '{tag['key']}'")

def lambda_handler(event, context):
    """AWS Lambda Function entrypoint to Load Splitter Example

    Parameters
    ----------
    event: dict, required
        - CloudTrail event
        - or SQS event
    context: object, required
        Lambda Context runtime methods and attributes
        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    -------
    dict
        statusCode: an integer success or failure status code
        count:      an integer count of the number of Tag Creation events processed
        body:       a string describing the processing that was performed

    Raises
    ------
    json.JSONDecodeError
        May be raised if an input SQS message does not contain JSON parsable information.
    """
    logger.setLevel(logging.INFO)
    logger.info(event)

    ret_val_ok         = { 'statusCode': 200, 'count': 0, 'body': '' }
    ret_val_ok_split   = { 'statusCode': 202, 'count': 0, 'body': 'event was accepted' }
    ret_val_ok_ignored = { 'statusCode': 202, 'count': 0, 'body': 'event was ignored, not a type of interest' }
    ret_val_err        = { 'statusCode': 400, 'count': 0, 'body': 'invalid event argument' }

    # try to parse event as an SQS message, in case the event came from our queue
    event_from_sqs = extract_event_from_queue_message(event)
    if event_from_sqs:
        # yes, the event is from our queue, so now we will just work with it
        event = event_from_sqs

    # try to confirm this is a CreateTags event, which is what we are interested in
    if not event or not event.get("detail",{}).get("eventName",None):
        logger.error(f"===> FAIL: unable to parse event (cannot find the 'eventName')\n{event}\n{ret_val_err}")
        return ret_val_err
    event_name = event.get("detail",{}).get("eventName",None)
    if not event_name == "CreateTags":
        logger.info(f"===> ignoring event of '{event_name}', since it is not of interest\n{ret_val_ok_ignored}")
        return ret_val_ok_ignored

    # try to find the list of tags that have been newly created
    if not event or not event.get("detail",{}).get("requestParameters",{}).get("tagSet",{}).get("items",None):
        logger.error(f"===> FAIL: unable to parse event (cannot find the 'tagSet')\n{event}\n{ret_val_err}")
        return ret_val_err
    tags = event.get("detail").get("requestParameters").get("tagSet").get("items")
    if not isinstance(tags, list):
        logger.error(f"===> FAIL: unable to parse event (cannot find the 'tagSet' as a list)\n{event}\n{ret_val_err}")
        return ret_val_err

    # process the the list of tags found
    logger.info(f"===> found '{len(tags)}' tag(s) to process")
    if len(tags) == 1:
        # just one tag, so we work on the tag here
        process_one_tag(tags[0])
        ret_val_ok['count'] = 1
        ret_val_ok['body'] = "handled 1 tag"
        logger.info(f"===> SUCCESS: processed 1 tag ({tags[0]['key']})\n{ret_val_ok}")
        return ret_val_ok
    # there was more than one tag, so we will queue 1 message per tag found
    queue_smaller_events(event)
    ret_val_ok_split['count'] = len(tags)
    ret_val_ok_split['body'] = f"split '{len(tags)}' tags into '{len(tags)}' queued messages"
    logger.info(f"===> SUCCESS: split '{len(tags)}' tags into '{len(tags)}' queued messages\n{ret_val_ok_split}")
    return ret_val_ok_split
