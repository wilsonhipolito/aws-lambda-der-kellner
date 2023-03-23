terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.59.0"
    }
  }
}

provider "aws" {
}


data "archive_file" "zip_the_python_code" {
  type        = "zip"
  source_dir  = "${path.module}/../src/"
  output_path = "${path.module}/../src/kellner.zip"
}

resource "aws_lambda_function" "kellner" {
  filename      = "${path.module}/../src/kellner.zip"
  function_name = "KellnerFunction"
  role          = aws_iam_role.lambda_role.arn
  handler       = "Kellner/app.lambda_handler"
  runtime       = "python3.8"
  environment {
    variables = {
      "SQS_QUEUE_URL" = aws_sqs_queue.kellner_queue.url
    }
  }
  depends_on = [
    aws_iam_role_policy_attachment.attach_iam_policy_to_iam_role,
    aws_s3_bucket.partner_bucket,
    aws_sqs_queue.kellner_queue
  ]
}

# Event source from S3
resource "aws_lambda_permission" "s3-lambda-permission" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = "${aws_lambda_function.kellner.arn}"
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.partner_bucket.arn
}
resource "aws_s3_bucket_notification" "lambda_trigger" {
  bucket = aws_s3_bucket.partner_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.kellner.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "AWSLogs/"
    filter_suffix       = ".csv"
  }
}