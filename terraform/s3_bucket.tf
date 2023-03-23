resource "aws_s3_bucket" "partner_bucket" {
  bucket = var.partner_s3_bucket_name
}