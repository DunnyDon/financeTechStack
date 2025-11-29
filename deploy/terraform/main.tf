terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ECS Cluster
resource "aws_ecs_cluster" "techstack" {
  name = var.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name = "techstack-cluster"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/techstack"
  retention_in_days = 7

  tags = {
    Name = "techstack-logs"
  }
}

# ECS Task Definition
resource "aws_ecs_task_definition" "techstack" {
  family                   = "techstack-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "techstack-app"
      image     = var.container_image
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "PREFECT_API_URL"
          value = "http://${aws_lb.prefect.dns_name}:4200/api"
        },
        {
          name  = "PYTHONUNBUFFERED"
          value = "1"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "python -c 'import sys; from src.main import aggregate_financial_data; print(\"OK\")' || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 5
      }
    }
  ])

  tags = {
    Name = "techstack-task"
  }
}

# IAM Roles
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "ecsTaskRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

# ECS Service
resource "aws_ecs_service" "techstack" {
  name            = var.service_name
  cluster         = aws_ecs_cluster.techstack.id
  task_definition = aws_ecs_task_definition.techstack.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnets
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.techstack.arn
    container_name   = "techstack-app"
    container_port   = 8000
  }

  depends_on = [
    aws_lb_listener.techstack,
    aws_iam_role.ecs_task_execution_role,
  ]

  tags = {
    Name = "techstack-service"
  }
}

# Load Balancer
resource "aws_lb" "prefect" {
  name               = "techstack-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = var.subnets

  tags = {
    Name = "techstack-alb"
  }
}

resource "aws_lb_target_group" "techstack" {
  name        = "techstack-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 3
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name = "techstack-tg"
  }
}

resource "aws_lb_listener" "techstack" {
  load_balancer_arn = aws_lb.prefect.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.techstack.arn
  }
}

# Security Groups
resource "aws_security_group" "alb" {
  name = "techstack-alb-sg"

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 4200
    to_port     = 4200
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "techstack-alb-sg"
  }
}

resource "aws_security_group" "ecs_tasks" {
  name = "techstack-ecs-tasks-sg"

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port   = 4200
    to_port     = 4200
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "techstack-ecs-tasks-sg"
  }
}

# Outputs
output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = aws_lb.prefect.dns_name
}

output "prefect_ui_url" {
  description = "URL to access Prefect UI"
  value       = "http://${aws_lb.prefect.dns_name}:4200"
}

output "app_url" {
  description = "URL to access the application"
  value       = "http://${aws_lb.prefect.dns_name}:8000"
}
