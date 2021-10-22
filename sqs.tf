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

# The queue to hold the smaller workloads that get created
resource "aws_sqs_queue" "lambda_invocation_queue" {
  name = "${var.prefix}_queue"
  #delay_seconds             = 90
  #message_retention_seconds = 1209600
  #receive_wait_time_seconds = 0
  kms_master_key_id                 = "alias/aws/sqs"
  kms_data_key_reuse_period_seconds = 300
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.lambda_invocation_queue_deadletter.arn
    maxReceiveCount     = 4
  })
}

# Dead Letter queue. Every SQS queue should have a dead letter queue.
resource "aws_sqs_queue" "lambda_invocation_queue_deadletter" {
  name                              = "${var.prefix}_queue_deadletter"
  kms_master_key_id                 = "alias/aws/sqs"
  kms_data_key_reuse_period_seconds = 300
}

# Connect the Queue to the Lambda (auto flow of queue msgs to the lambda)
resource "aws_lambda_event_source_mapping" "sqs" {
  event_source_arn = aws_sqs_queue.lambda_invocation_queue.arn
  function_name    = aws_lambda_function.load_splitter.arn
  batch_size       = 1
}
