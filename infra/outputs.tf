output "app_url" {
  description = "Public URL of the application"
  value       = "https://${local.domain}"
}

output "alb_dns" {
  description = "ALB DNS name (use if domain not yet wired)"
  value       = aws_lb.main.dns_name
}

output "ecr_repository_url" {
  description = "ECR repository URL for docker push"
  value       = aws_ecr_repository.app.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.app.name
}

output "rds_endpoint" {
  description = "RDS hostname (private, not publicly accessible)"
  value       = aws_db_instance.main.address
  sensitive   = true
}

output "github_actions_role_arn" {
  description = "ARN to set as AWS_ROLE_ARN in GitHub repository variables"
  value       = aws_iam_role.github_actions.arn
}

output "route53_nameservers" {
  description = "Paste these 4 nameservers into name.com → Manage DNS → Nameservers for alsotheseer.com"
  value       = aws_route53_zone.main.name_servers
}
