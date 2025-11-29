variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "ECS cluster name"
  type        = string
  default     = "techstack-cluster"
}

variable "service_name" {
  description = "ECS service name"
  type        = string
  default     = "techstack-service"
}

variable "container_image" {
  description = "Docker image URI"
  type        = string
}

variable "task_cpu" {
  description = "ECS task CPU (256, 512, 1024, 2048, 4096)"
  type        = string
  default     = "512"
}

variable "task_memory" {
  description = "ECS task memory in MB"
  type        = string
  default     = "1024"
}

variable "desired_count" {
  description = "Desired number of tasks"
  type        = number
  default     = 1
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnets" {
  description = "List of subnet IDs"
  type        = list(string)
}
