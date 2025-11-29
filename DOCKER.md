# Docker & Cloud Deployment Guide

Complete guide for containerizing and deploying Finance TechStack to Docker, AWS, Kubernetes, and other cloud platforms.

## Table of Contents

1. [Local Docker Setup](#local-docker-setup)
2. [Docker Compose (Recommended)](#docker-compose-recommended)
3. [Service Configuration](#service-configuration)
4. [AWS ECS Deployment](#aws-ecs-deployment)
5. [Kubernetes Deployment](#kubernetes-deployment)
6. [Other Cloud Platforms](#other-cloud-platforms)
7. [Scaling with Dask and Coiled](#scaling-with-dask-and-coiled)
8. [Troubleshooting](#troubleshooting)

## Local Docker Setup

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- AWS CLI (for AWS deployment)
- Terraform (for IaC deployment)
- kubectl (for Kubernetes)

### Building the Docker Image

```bash
# Build the image locally
docker build -t finance-techstack:latest .

# Build with specific tag
docker build -t finance-techstack:v0.1.0 .

# Build with build arguments
docker build \
  --build-arg PYTHON_VERSION=3.13 \
  -t finance-techstack:latest .
```

### Running Single Container

```bash
# Run with default settings
docker run -it finance-techstack:latest

# Run with environment variables
docker run -it \
  -e PREFECT_API_URL=http://localhost:4200/api \
  -e ALPHA_VANTAGE_API_KEY=your_key_here \
  finance-techstack:latest

# Mount volumes for data persistence
docker run -it \
  -v $(pwd)/db:/app/db \
  -v $(pwd)/config.csv:/app/config.csv \
  -p 8000:8000 \
  finance-techstack:latest

# Run tests
docker run -it \
  finance-techstack:latest \
  python -m pytest tests/ -v

# Interactive shell
docker run -it \
  --entrypoint /bin/bash \
  finance-techstack:latest
```

## Docker Compose (Recommended)

### Quick Start

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f techstack

# Stop services
docker-compose down

# Remove all data
docker-compose down -v
```

### Services Included

The `docker-compose.yml` includes:

1. **PostgreSQL** - Database for Prefect state
2. **Prefect Server** - Workflow orchestration UI & API
3. **Prefect Worker** - Task execution engine
4. **Finance TechStack App** - Main application
5. **Redis** - Optional caching layer

### Configuration

```bash
# Set environment variables
export POSTGRES_PASSWORD=your-secure-password
export ALPHA_VANTAGE_API_KEY=your_api_key
export AWS_ACCOUNT_ID=123456789012

# Create .env file
cat > .env << EOF
POSTGRES_PASSWORD=secure-password-here
ALPHA_VANTAGE_API_KEY=your_api_key
AWS_ACCOUNT_ID=123456789012
EOF

docker-compose up
```

### Running Tests in Docker

```bash
# Run all tests
docker-compose run --rm techstack python -m pytest tests/ -v

# Run specific test file
docker-compose run --rm techstack python -m pytest tests/test_sec_scraper.py -v

# Run with coverage
docker-compose run --rm techstack python -m pytest tests/ --cov=src
```

### Running the Application

```bash
# Run the main aggregation flow
docker-compose run --rm techstack python src/main.py

# Run with custom tickers
docker-compose run --rm techstack python -c \
  "from src.main import aggregate_financial_data; \
   result = aggregate_financial_data(['GOOGL', 'AMZN']); \
   print(result)"

# Schedule recurring execution with Prefect
docker-compose run --rm techstack python -m prefect deployment build \
  -n "daily-aggregation" \
  -sb local \
  src/main.py:aggregate_financial_data
```

### Accessing Services

- **Prefect UI**: http://localhost:4200
- **Application**: http://localhost:8000
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

### Data Persistence

Data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep techstack

# Inspect volume
docker volume inspect techstack_postgres_data

# Backup data
docker run --rm \
  -v techstack_postgres_data:/data \
  -v $(pwd):/backup \
  postgres:15-alpine \
  pg_dump -U techstack -h postgres techstack > ./backup/techstack.sql
```

## AWS ECS Deployment

### Prerequisites

```bash
# Configure AWS CLI
aws configure

# Set environment variables
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1
export ECR_REPOSITORY_NAME=finance-techstack
```

### Step 1: Create ECR Repository

```bash
# Create repository
aws ecr create-repository \
  --repository-name $ECR_REPOSITORY_NAME \
  --region $AWS_REGION

# Get repository URI
ECR_REPO_URI=$(aws ecr describe-repositories \
  --repository-names $ECR_REPOSITORY_NAME \
  --region $AWS_REGION \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo $ECR_REPO_URI
```

### Step 2: Build and Push to ECR

```bash
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and tag image
docker build -t $ECR_REPOSITORY_NAME:latest .
docker tag $ECR_REPOSITORY_NAME:latest $ECR_REPO_URI:latest

# Push to ECR
docker push $ECR_REPO_URI:latest
```

### Step 3: Create ECS Resources

```bash
# Create IAM roles
bash deploy/aws-iam-setup.sh

# Update task definition with ECR URI
sed -i "s|ACCOUNT_ID|$AWS_ACCOUNT_ID|g" deploy/ecs-task-definition.json
sed -i "s|REGION|$AWS_REGION|g" deploy/ecs-task-definition.json

# Register task definition
aws ecs register-task-definition \
  --cli-input-json file://deploy/ecs-task-definition.json \
  --region $AWS_REGION

# Create cluster
aws ecs create-cluster \
  --cluster-name techstack-cluster \
  --region $AWS_REGION

# Create service
aws ecs create-service \
  --cluster techstack-cluster \
  --service-name techstack-service \
  --task-definition techstack-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx,subnet-yyy],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --region $AWS_REGION
```

### Step 4: Automated Deployment Script

```bash
# Use deployment script
bash deploy/aws-ecs-deploy.sh

# Or with custom variables
AWS_ACCOUNT_ID=123456789012 \
AWS_REGION=us-west-2 \
IMAGE_TAG=v0.1.0 \
bash deploy/aws-ecs-deploy.sh
```

### View Deployment Status

```bash
# Check service status
aws ecs describe-services \
  --cluster techstack-cluster \
  --services techstack-service \
  --region $AWS_REGION

# View task logs
aws logs tail /ecs/techstack --follow --region $AWS_REGION

# Update service
aws ecs update-service \
  --cluster techstack-cluster \
  --service techstack-service \
  --force-new-deployment \
  --region $AWS_REGION
```

## AWS Infrastructure as Code (Terraform)

### Setup

```bash
cd deploy/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars << EOF
aws_region      = "us-east-1"
cluster_name    = "techstack-cluster"
service_name    = "techstack-service"
container_image = "${AWS_ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/finance-techstack:latest"
task_cpu        = "512"
task_memory     = "1024"
desired_count   = 2
vpc_id          = "vpc-xxxxx"
subnets         = ["subnet-xxxxx", "subnet-yyyyy"]
EOF
```

### Deploy

```bash
# Plan deployment
terraform plan

# Apply configuration
terraform apply

# Get outputs
terraform output

# Destroy resources
terraform destroy
```

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl

# Configure kubectl
kubectl config use-context <your-cluster-context>

# Verify connection
kubectl cluster-info
```

### Deploy to Kubernetes

```bash
# Create namespace
kubectl create namespace techstack

# Create secrets
kubectl create secret generic techstack-secrets \
  --from-literal=alpha-vantage-api-key=your_key_here \
  -n techstack

# Create ConfigMap
kubectl create configmap techstack-config \
  --from-file=config.csv=./config.csv \
  -n techstack

# Deploy application
kubectl apply -f deploy/kubernetes/deployment.yaml -n techstack

# Check deployment status
kubectl get deployments -n techstack
kubectl get pods -n techstack
kubectl get svc -n techstack

# View logs
kubectl logs -f deployment/techstack-app -n techstack

# Access service
kubectl port-forward svc/techstack-service 8000:80 -n techstack
```

### Scale Deployment

```bash
# Manual scaling
kubectl scale deployment techstack-app --replicas=5 -n techstack

# Autoscaling (HPA already configured)
kubectl get hpa -n techstack
```

## Other Cloud Platforms

### Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT_ID/finance-techstack

# Deploy to Cloud Run
gcloud run deploy finance-techstack \
  --image gcr.io/PROJECT_ID/finance-techstack \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 2 \
  --set-env-vars PREFECT_API_URL=https://prefect-server.example.com/api
```

### Azure Container Instances

```bash
# Build and push to Azure Container Registry
az acr build --registry myregistry \
  --image finance-techstack:latest .

# Deploy container instance
az container create \
  --resource-group mygroup \
  --name techstack \
  --image myregistry.azurecr.io/finance-techstack:latest \
  --cpu 2 \
  --memory 2 \
  --environment-variables PREFECT_API_URL=http://prefect-server:4200/api
```

### DigitalOcean App Platform

```bash
# Create app spec
cat > app.yaml << EOF
name: finance-techstack
services:
- name: app
  github:
    repo: your-repo/finance-techstack
    branch: main
  dockerfile_path: Dockerfile
  http_port: 8000
  envs:
  - key: PREFECT_API_URL
    value: http://prefect-server:4200/api
EOF

# Deploy
doctl apps create --spec app.yaml
```

## Monitoring & Logging

### CloudWatch (AWS)

```bash
# View logs
aws logs tail /ecs/techstack --follow

# Create custom metric
aws cloudwatch put-metric-data \
  --metric-name TaskCount \
  --value 1 \
  --namespace TechStack
```

### Prometheus & Grafana

```bash
# Add to docker-compose.yml
docker-compose up prometheus grafana

# Access Grafana
# URL: http://localhost:3000
# Default credentials: admin/admin
```

### Datadog

```bash
# Set Datadog API key
export DD_API_KEY=your_api_key

# Run with Datadog agent
docker run -e DD_AGENT_HOST=datadog -e DD_TRACE_ENABLED=true \
  finance-techstack:latest
```

## Troubleshooting

### Docker Build Issues

```bash
# Check Docker daemon
docker ps

# Remove dangling images
docker image prune -a

# Rebuild without cache
docker build --no-cache -t finance-techstack:latest .

# Debug build
docker build --progress=plain -t finance-techstack:latest .
```

### Container Runtime Issues

```bash
# View container logs
docker logs <container-id>

# Inspect running container
docker exec -it <container-id> /bin/bash

# Check resource usage
docker stats <container-id>

# Remove stuck containers
docker rm -f <container-id>
```

### Network Issues

```bash
# Test DNS resolution
docker run --rm alpine nslookup prefect-server

# Check network connectivity
docker network ls
docker network inspect techstack-network

# Inspect port mappings
docker port <container-id>
```

### Persistence Issues

```bash
# Check volumes
docker volume ls

# Verify mount paths
docker inspect <container-id> | grep -A 10 Mounts

# Backup volume data
docker run --rm -v volume-name:/data -v $(pwd):/backup \
  alpine tar czf /backup/volume-backup.tar.gz /data
```

## Best Practices

1. **Security**
   - Never commit secrets to git
   - Use environment variables or secret management services
   - Run containers as non-root user
   - Scan images for vulnerabilities

2. **Performance**
   - Use multi-stage builds to reduce image size
   - Minimize layers in Dockerfile
   - Cache dependencies
   - Use health checks

3. **Reliability**
   - Configure automatic restarts
   - Set resource limits
   - Implement health checks
   - Use load balancers

4. **Operations**
   - Tag images with versions
   - Maintain multiple environments (dev, staging, prod)
   - Log to centralized system
   - Monitor resource usage

## Scaling with Dask and Coiled

### Overview

While your current single Prefect worker handles basic SEC filings and financial data aggregation, Dask provides distributed computing capabilities for scaling analysis across multiple machines. Coiled is the managed Dask platform that handles cluster orchestration on AWS.

### Use Cases for Dask Integration

1. **Batch Processing Multiple Companies**
   - Process thousands of companies' SEC filings in parallel
   - Current: Sequential CIK lookups and filing downloads
   - With Dask: Distributed across worker cluster

2. **XBRL Data Analysis**
   - Complex financial metric calculations across datasets
   - Time-series analysis across multiple quarters/years
   - Correlation and regression analysis across company universes

3. **Data Merge Operations**
   - Joining multiple data sources (SEC, Alpha Vantage, etc.)
   - Large historical dataset aggregations
   - Real-time fundamentals scoring

4. **Bulk Analytics**
   - Computing financial ratios for entire markets
   - Sector/industry comparisons
   - Anomaly detection across filing datasets

### Architecture Recommendations

#### Option 1: Prefect + Dask (Recommended for Current Stack)

**Approach**: Use Dask within Prefect tasks for parallelization

```yaml
# docker-compose.yml additions
services:
  dask-scheduler:
    image: dask/dask:latest
    container_name: techstack-dask-scheduler
    ports:
      - "8786:8786"  # Scheduler TCP
      - "8787:8787"  # Bokeh dashboard
    command: dask-scheduler
    networks:
      - techstack-network

  dask-worker:
    image: dask/dask:latest
    container_name: techstack-dask-worker
    command: dask-worker tcp://dask-scheduler:8786
    depends_on:
      - dask-scheduler
    deploy:
      replicas: 3  # Scale to more workers as needed
    networks:
      - techstack-network
```

**Integration Pattern**:
```python
# In your Prefect flows
from dask.distributed import Client
from prefect import task, flow

@flow
def batch_process_companies(tickers: list):
    with Client("tcp://dask-scheduler:8786") as client:
        # Distribute CIK lookups
        ciks = client.map(fetch_company_cik, tickers)
        
        # Distribute filing fetches
        filings = client.map(fetch_sec_filings, ciks)
        
        # Gather and save results
        results = client.gather(filings)
    return results
```

**Pros**:
- Tight integration with Prefect
- Local development with docker-compose
- Fine-grained control over task distribution
- No vendor lock-in

**Cons**:
- Requires cluster management
- Manual scaling configuration
- Monitoring complexity

#### Option 2: Coiled (Managed Dask)

**Approach**: Managed Dask clusters on AWS via Coiled

```python
# example_coiled_integration.py
import coiled
import dask.dataframe as dd
from prefect import flow, task

@task
def process_with_coiled(companies_df):
    """Process companies data with Coiled cluster"""
    # Create managed cluster
    cluster = coiled.Cluster(
        n_workers=10,
        worker_memory="4GB",
        scheduler_memory="4GB",
        region="us-west-2",
        spot_instances=True  # Cost optimization
    )
    
    with cluster.get_client() as client:
        # Convert to Dask DataFrame
        ddf = dd.from_pandas(companies_df, npartitions=20)
        
        # Distributed operations
        result = ddf.groupby('sector').aggregate({
            'revenue': 'sum',
            'net_income': 'mean'
        }).compute()
    
    return result
```

**Infrastructure (Kubernetes with Coiled)**:
```yaml
# deploy/kubernetes/coiled-integration.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: techstack-monthly-analysis
spec:
  schedule: "0 2 1 * *"  # 2 AM on 1st of month
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: techstack
            image: finance-techstack:latest
            env:
            - name: COILED_API_KEY
              valueFrom:
                secretKeyRef:
                  name: coiled-credentials
                  key: api-key
            command: ["python", "src/batch_analysis.py"]
          restartPolicy: OnFailure
```

**Pros**:
- Fully managed infrastructure
- Auto-scaling
- Cost optimization with spot instances
- Built-in monitoring and profiling
- Integrated security/authentication

**Cons**:
- Vendor lock-in to Coiled
- Subscription cost (~$300-500/month for clusters)
- AWS account required
- Additional dependency

### Implementation Roadmap

**Phase 1: Local Dask Testing** (2-3 weeks)
```
1. Add Dask scheduler/workers to docker-compose.yml
2. Create sample Dask workflow in tests/
3. Benchmark against current Prefect-only approach
4. Document scaling characteristics
```

**Phase 2: Coiled Evaluation** (1 week)
```
1. Set up Coiled free tier
2. Run pilot batch job (1000 companies)
3. Compare cost vs. self-hosted Dask
4. Document authentication flow
```

**Phase 3: Production Integration** (3-4 weeks)
```
1. Create abstraction layer for Dask vs. Coiled
2. Implement retry/fault tolerance
3. Add monitoring and alerting
4. Document ops procedures
```

### Configuration Recommendations

**For Current Use Case (10-100 companies)**:
- Start with **Prefect alone** (current setup is optimal)
- No Dask needed yet

**For Medium Scale (100-1000 companies)**:
- Add **local Dask cluster** in docker-compose
- 3-5 worker nodes
- Use Prefect for orchestration, Dask for data operations

**For Enterprise Scale (1000+ companies, real-time)**:
- Use **Coiled** for managed infrastructure
- Auto-scaling (5-50 workers based on load)
- Spot instances for cost optimization
- Separate cluster for batch vs. streaming

### Cost Analysis

| Scenario | Solution | Monthly Cost | Notes |
|----------|----------|--------------|-------|
| 100 companies | Prefect only | $0 | Self-hosted, current setup |
| 500 companies | Local Dask | $50-100 | EC2 instances for nodes |
| 5000 companies | Coiled | $400-800 | Managed, auto-scaling |
| Real-time 24/7 | Coiled + K8s | $1200+ | Continuous cluster |

### Data Bottlenecks to Consider

**Before Adding Dask, optimize**:
1. **SEC API**: Currently rate-limited (1 req/sec). Dask won't help unless you control multiple API tokens
2. **Alpha Vantage**: Free tier is 5 API/min. Upgrade to higher tier before parallelizing
3. **Network**: Bandwidth constraints between workers
4. **Storage**: Ensure Parquet storage can handle distributed writes (PostgreSQL preferred over filesystem)

## Next Steps

- [ ] Configure CI/CD pipeline (GitHub Actions, GitLab CI)
- [ ] Set up monitoring and alerting
- [ ] Implement database backup strategy
- [ ] Configure log aggregation
- [ ] Set up disaster recovery procedures
- [ ] Evaluate Dask for batch processing
- [ ] Create Coiled account for pilot testing

## Support

For issues or questions:
1. Check Docker documentation: https://docs.docker.com
2. Review Prefect documentation: https://docs.prefect.io
3. Check AWS/Kubernetes documentation
4. Open issue on GitHub: https://github.com/DunnyDon/financeTechStack/issues
