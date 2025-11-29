#!/bin/bash
# AWS ECS task deployment script

set -e

# Configuration
AWS_ACCOUNT_ID=${AWS_ACCOUNT_ID}
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REPOSITORY_NAME=${ECR_REPOSITORY_NAME:-finance-techstack}
IMAGE_TAG=${IMAGE_TAG:-latest}
CLUSTER_NAME=${CLUSTER_NAME:-techstack-cluster}
SERVICE_NAME=${SERVICE_NAME:-techstack-service}
TASK_FAMILY=${TASK_FAMILY:-techstack-task}

echo "Deploying Finance TechStack to AWS ECS..."
echo "Region: $AWS_REGION"
echo "Repository: $ECR_REPOSITORY_NAME"
echo "Image Tag: $IMAGE_TAG"

# Get ECR login token
echo "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build Docker image
echo "Building Docker image..."
docker build -t $ECR_REPOSITORY_NAME:$IMAGE_TAG .
docker tag $ECR_REPOSITORY_NAME:$IMAGE_TAG \
    $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG

# Push to ECR
echo "Pushing image to ECR..."
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY_NAME:$IMAGE_TAG

# Update ECS service
echo "Updating ECS service..."
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service $SERVICE_NAME \
    --force-new-deployment \
    --region $AWS_REGION

echo "Deployment complete!"
echo "Access Prefect UI at: https://<load-balancer-url>:4200"
