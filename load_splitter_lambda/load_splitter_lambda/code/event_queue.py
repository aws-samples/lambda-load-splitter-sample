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

import copy
import json
import logging
import os
import sys

import boto3
import botocore

sys.path.append("load_splitter_lambda/code") # needed for aws and pytest

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def enqueue_event(event):
    # -*- coding: utf-8 -*-
    """This method takes a event and enqueues it as a JSON string in an SQS Queue. The
    name of the Queue is found in the "QUEUE_NAME" environment.

    Parameters
    ----------
    event : list or dict
        The incoming data event that should be enqueued. Typically this is a python
        representation of JSON, in an arbitrarily nested list or dict object.
    """
    try:
        sqs = boto3.resource("sqs")
        queue_name = os.environ["QUEUE_NAME"]
        if not queue_name or len(queue_name) == 0:
            logger.error(f"===> FAIL: unable to find environment variable QUEUE_NAME")
            return
        logger.info(f"===> queueing a message to queue '{queue_name}'...")
        queue = sqs.get_queue_by_name(QueueName=queue_name)
        queue.send_message(MessageBody=json.dumps(event))
    except botocore.exceptions.ClientError as ex:
        logger.error(f"===> EXCEPTION CAUGHT: while queueing message to SQS queue named '{queue_name}'")
        raise ex

def get_reference_to_embedded_list(event):
    # -*- coding: utf-8 -*-
    """This method takes a dict of the format shown below, and returns a reference to
    the "items" list found inside it. If the incoming 'event' parameter doesn't have the
    expected format, an empty list is returned.

    Here is an example input which has the required structure. The list [1,2,3] would be
    returned with this as the incoming 'event' parameter:

        {
            "detail": {
                "requestParameters": {
                    "tagSet": {
                        "items": [ 1, 2, 3 ]
                    }
                }
            }
        }

    Parameters
    ----------
    event : dict
        The incoming dict should have the structure shown ealier with the "items" key in
        it. If it doesn't have that structure, then 'None' will be returned.

    Returns
    -------
    list
        The returned list will have the value of the nested "items" key as found in the
        incoming 'event' parameter. If that key is not found, then an empty list will be
        returned.
    """
    if not event:
        return []
    return event.get("detail",{}).get("requestParameters",{}).get("tagSet",{}).get("items",[])

def queue_smaller_events(event):
    # -*- coding: utf-8 -*-
    """This method takes an event parameter and finds an embedded list of interest inside
    it. If there is more than 1 item in the list, then this method iteratively enqueues to
    SQS the same original incoming event, but each time replacing the embedded list with
    an updated list, containing just one of the items from the original list. Thus this
    method has the effect of breaking down large events into multiple smaller events and
    enqueing them.

    Parameters
    ----------
    event : dict
        The incoming dict should have the structure documented in the
        get_reference_to_embedded_list() method above. When it has that structure, the
        list found in the "items" key is used as described earlier. If the incoming dict
        does not have the expected structure, this method does nothing.
    """
    event_copy = copy.deepcopy(event) # work with a copy, so caller sees no changes
    list_reference = get_reference_to_embedded_list(event_copy)
    list_items = list_reference.copy() # iterate through copy of list, as list will be changing
    if len(list_items) == 1:
        return
    for item in list_items:
        list_reference.clear()
        list_reference.append(item)
        enqueue_event(event_copy)

def extract_event_from_queue_message(queued_event_message):
    # -*- coding: utf-8 -*-
    """This method takes a 'queued_event_message', and if it is an SQS structure (i.e. if
    'eventSource' is 'aws:sqs'), then it extracts and returns just the value of the "body"
    key within it, but it returns it not as a string, but as the JSON the string encodes.
    For examples of how to use this method, see the accompanying unit tests.

    Parameters
    ----------
    queued_event_message : dict
        This parameter holds the event as read from an SQS Queue.
        - Note that if 'queued_event_message' is not recognized as an SQS event structure,
        then this method will return the value 'None'.
        - Note that if 'queued_event_message' is an SQS event structure, but "body" can't
        be found, it will return the value None
        - Note that if the "body" value can't be parsed as JSON, then an exception
        will be raised (json.JSONDecodeError)

    Returns
    -------
    dict or list
        The return value is a dict or list containing the JSON as decoded from the value
        of the "body" key found in the input parameter.
    """
    if not 'Records' in queued_event_message:
        return None
    for record in queued_event_message['Records']:
        if (record.get("eventSource",None) == 'aws:sqs') and 'body' in record:
            return(json.loads(record["body"].replace("'", '"')))
        else:
            return None
