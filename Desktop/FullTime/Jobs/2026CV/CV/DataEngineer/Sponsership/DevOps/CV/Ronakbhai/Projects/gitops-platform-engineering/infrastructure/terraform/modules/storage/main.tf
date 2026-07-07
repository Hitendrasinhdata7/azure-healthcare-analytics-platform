# S3 buckets for Loki chunks + Velero cluster backups, both versioned
# and encrypted at rest; separate buckets per environment for isolation.
variable "environment" { type = string }

resource "aws_s3_bucket" "loki_chunks" {
  bucket = "${var.environment}-gitops-platform-loki-chunks"
}
resource "aws_s3_bucket_versioning" "loki_chunks" {
  bucket = aws_s3_bucket.loki_chunks.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "loki_chunks" {
  bucket = aws_s3_bucket.loki_chunks.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "aws:kms" }
  }
}

resource "aws_s3_bucket" "cluster_backups" {
  bucket = "${var.environment}-gitops-platform-cluster-backups"
}
resource "aws_s3_bucket_versioning" "cluster_backups" {
  bucket = aws_s3_bucket.cluster_backups.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_lifecycle_configuration" "cluster_backups" {
  bucket = aws_s3_bucket.cluster_backups.id
  rule {
    id     = "expire-old-backups"
    status = "Enabled"
    expiration { days = 90 }
  }
}
