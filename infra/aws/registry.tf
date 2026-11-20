# One ECR repository per image. A tag is never moved once pushed: the tag in
# terraform.tfvars always names the same code.

resource "aws_ecr_repository" "this" {
  for_each = toset(["proxy", "frontend", "backend"])

  name                 = "easy-diligence/${each.key}"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

locals {
  images = {
    for service, repository in aws_ecr_repository.this :
    service => "${repository.repository_url}:${var.image_tag}"
  }
}
