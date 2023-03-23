resource "aws_iam_role" "lambda_role" {
  name               = "kellner_iam_role"
  assume_role_policy = <<EOF
  {
   "Version": "2012-10-17",
   "Statement": [
     {
       "Action": "sts:AssumeRole",
       "Principal": {
         "Service": "lambda.amazonaws.com"
       },
       "Effect": "Allow",
       "Sid": ""
     }
   ]
  }
  EOF
}

resource "aws_iam_policy" "iam_policy_for_lambda" {
  name        = "kellner_aws_lambda_role_policy"
  path        = "/"
  description = "AWS IAM Policy for managing aws lambda role"
  policy      = <<EOF
{
 "Version": "2012-10-17",
 "Statement": [
   {
      "Action": [
       "logs:CreateLogGroup",
       "logs:CreateLogStream",
       "logs:PutLogEvents"
     ],
     "Resource": "arn:aws:logs:*:*:*",
     "Effect": "Allow"
   },
   {
      "Action": "s3:*",
      "Resource": "${aws_s3_bucket.partner_bucket.arn}",
      "Effect": "Allow"
   },
   {
      "Action": "sqs:SendMessage",
      "Resource": "${aws_sqs_queue.kellner_queue.arn}",
      "Effect": "Allow"
   }
 ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "attach_iam_policy_to_iam_role" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = aws_iam_policy.iam_policy_for_lambda.arn
}
