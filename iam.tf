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

# The IAM Policy Document that defines the permissions that the "load_splitter_lambda"
# lambda function will have a run-time.
data "aws_iam_policy_document" "load_splitter_lambda" {
  statement {
    actions = [
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:SendMessage",
    ]
    resources = [
      aws_sqs_queue.lambda_invocation_queue.arn
    ]
  }
  statement {
    actions   = ["logs:CreateLogGroup"]
    resources = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${var.prefix}_lambda:*"]
  }
}

# The IAM Policy Document that defines what services can assume the Role to be created
data "aws_iam_policy_document" "lambda_assumerole" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

# The IAM Policy to create which will hold the policy document above.
resource "aws_iam_policy" "load_splitter_lambda" {
  name_prefix = "${var.prefix}_"
  policy      = data.aws_iam_policy_document.load_splitter_lambda.json
}

# The IAM Role that holds the above policy and that the "load_splitter_lambda"
# lambda function will have a run-time, and who can assume the role.
resource "aws_iam_role" "load_splitter_lambda" {
  name_prefix        = "${var.prefix}_"
  assume_role_policy = data.aws_iam_policy_document.lambda_assumerole.json
}

# Attach the Policy to the Role
resource "aws_iam_role_policy_attachment" "load_splitter_lambda" {
  role       = aws_iam_role.load_splitter_lambda.id
  policy_arn = aws_iam_policy.load_splitter_lambda.arn
}
