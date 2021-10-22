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

# Define the Lambda that will do the splitting and processing
resource "aws_lambda_function" "load_splitter" {
  function_name    = "${var.prefix}_lambda"
  description      = "example lambda that takes a large payload, splits it into smaller pieces, and queues with SQS"
  filename         = "load_splitter_lambda.zip"
  source_code_hash = data.archive_file.load_splitter_lambda_zip.output_base64sha256
  role             = aws_iam_role.load_splitter_lambda.arn
  handler          = "load_splitter_lambda.code.main.lambda_handler"
  runtime          = "python3.8"
  timeout          = "30"
  environment {
    variables = {
      "QUEUE_NAME" = aws_sqs_queue.lambda_invocation_queue.name
    }
  }
}

# have terraform zip of the code for you (but without files it doesn't need)
data "archive_file" "load_splitter_lambda_zip" {
  type        = "zip"
  source_dir  = "load_splitter_lambda"
  output_path = "load_splitter_lambda.zip"
  excludes = [
    "requirements.txt", "requirements_dev.txt",
    "load_splitter_lambda/tests", "tox.ini", "setup.py",
    "load_splitter_lambda/__pycache__", "load_splitter_lambda/code/__pycache__",
    "pyproject.toml", ".pytest_cache", ".tox", "UNKNOWN.egg-info",
  ]
}

# Permit CloudWatch to call the Lambda (i.e. to trigger the lambda when the tags change)
resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.load_splitter.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ec2_events.arn
}

# Connect CloudWatch to the Lambda (i.e. trigger the lambda when the tags change)
resource "aws_cloudwatch_event_target" "trigger_lambda_when_tags_change" {
  rule = aws_cloudwatch_event_rule.ec2_events.name
  arn  = aws_lambda_function.load_splitter.arn
}
