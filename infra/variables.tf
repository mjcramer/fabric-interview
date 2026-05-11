variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-west-2"
}

variable "github_org" {
  description = "GitHub org or username that owns the repo"
  type        = string
  default     = "mjcramer"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "fabric-interview"
}

variable "app_port" {
  description = "Port the FastAPI container listens on"
  type        = number
  default     = 8000
}

variable "task_cpu" {
  description = "ECS task CPU units (1024 = 1 vCPU)"
  type        = number
  default     = 256
}

variable "task_memory" {
  description = "ECS task memory in MiB"
  type        = number
  default     = 512
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "aeo"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "aeo_app"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}
