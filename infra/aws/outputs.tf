output "url" {
  description = "The address of the application."
  value       = local.public_url
}

output "load_balancer_dns_name" {
  description = "The load balancer's address: the target of the DNS record of domain_name (README)."
  value       = aws_lb.this.dns_name
}

output "repositories" {
  description = "The ECR repositories, for docker push (README)."
  value       = { for service, repository in aws_ecr_repository.this : service => repository.repository_url }
}

output "cluster" {
  description = "The ECS cluster, for aws ecs update-service and execute-command (README)."
  value       = aws_ecs_cluster.this.name
}

output "openai_secret" {
  description = "The secret of the OpenAI key, for aws secretsmanager put-secret-value (README)."
  value       = aws_secretsmanager_secret.openai_api_key.name
}

output "database_endpoint" {
  description = "The PostgreSQL instance (reachable from the VPC only)."
  value       = aws_db_instance.this.address
}
