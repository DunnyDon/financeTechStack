# Deployment Guide

## Local Development

```bash
# Development server with auto-reload
uv run prefect server start
```

## Docker

### Build Image

```bash
docker build -t techstack:latest .
```

### Run Container

```bash
docker run \
  --env-file config.env \
  -v $(pwd)/db:/app/db \
  -p 8080:8080 \
  techstack:latest
```

## AWS ECS

### 1. Create IAM Role

Create role with policies:
- `AmazonECSTaskExecutionRolePolicy`
- `CloudWatchLogsFullAccess`
- `S3FullAccess` (for Parquet storage)

### 2. Push Image to ECR

```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

docker tag techstack:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/techstack:latest

docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/techstack:latest
```

### 3. Create ECS Task Definition

```json
{
  "family": "techstack-portfolio-analysis",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "techstack",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/techstack:latest",
      "essential": true,
      "environment": [
        {
          "name": "REPORT_EMAIL",
          "value": "your-email@example.com"
        }
      ],
      "secrets": [
        {
          "name": "SENDER_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:techstack/sender-password"
        },
        {
          "name": "ALPHA_VANTAGE_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:techstack/alpha-vantage-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/techstack",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### 4. Run ECS Task

```bash
aws ecs run-task \
  --cluster default \
  --task-definition techstack-portfolio-analysis \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}"
```

### 5. Schedule with EventBridge

Create scheduled rule:

```bash
aws events put-rule \
  --name techstack-daily-4pm \
  --schedule-expression "cron(0 16 * * ? *)"

aws events put-targets \
  --rule techstack-daily-4pm \
  --targets "Id"="1","Arn"="arn:aws:ecs:us-east-1:ACCOUNT:cluster/default","RoleArn"="arn:aws:iam::ACCOUNT:role/EventBridgeECSRole","EcsParameters"="{\"TaskDefinitionArn\":\"arn:aws:ecs:us-east-1:ACCOUNT:task-definition/techstack-portfolio-analysis:1\",\"LaunchType\":\"FARGATE\",\"NetworkConfiguration\":{\"awsvpcConfiguration\":{\"Subnets\":[\"subnet-xxx\"],\"SecurityGroups\":[\"sg-xxx\"]}}}"
```

## Kubernetes

### Deploy with Helm

```bash
helm repo add techstack https://your-helm-repo
helm install techstack-app techstack/techstack \
  --set image.tag=latest \
  --set config.reportEmail=your-email@example.com \
  --set config.alphaVantageKey=$ALPHA_VANTAGE_KEY
```

### Manual Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: techstack-portfolio-analysis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: techstack
  template:
    metadata:
      labels:
        app: techstack
    spec:
      containers:
      - name: techstack
        image: techstack:latest
        env:
        - name: REPORT_EMAIL
          value: "your-email@example.com"
        - name: SENDER_PASSWORD
          valueFrom:
            secretKeyRef:
              name: techstack-secrets
              key: sender-password
        - name: ALPHA_VANTAGE_KEY
          valueFrom:
            secretKeyRef:
              name: techstack-secrets
              key: alpha-vantage-key
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        volumeMounts:
        - name: data
          mountPath: /app/db
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: techstack-pvc

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: techstack-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi

---
apiVersion: batch/v1
kind: CronJob
metadata:
  name: techstack-daily-analysis
spec:
  schedule: "0 16 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: techstack
            image: techstack:latest
            command:
            - /bin/sh
            - -c
            - uv run python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow(send_email_report=True)"
            env:
            - name: REPORT_EMAIL
              valueFrom:
                configMapKeyRef:
                  name: techstack-config
                  key: report-email
          restartPolicy: OnFailure
```

Deploy:

```bash
kubectl apply -f k8s-deployment.yaml
kubectl create secret generic techstack-secrets \
  --from-literal=sender-password=$SENDER_PASSWORD \
  --from-literal=alpha-vantage-key=$ALPHA_VANTAGE_KEY
```

## Environment Variables

All supported configuration variables:

| Variable | Required | Example |
|----------|----------|---------|
| `REPORT_EMAIL` | Yes | user@example.com |
| `SENDER_EMAIL` | Yes | gmail@gmail.com |
| `SENDER_PASSWORD` | Yes | app-specific-password |
| `SMTP_HOST` | No | smtp.gmail.com |
| `SMTP_PORT` | No | 587 |
| `ALPHA_VANTAGE_KEY` | No | DEMO |
| `PREFECT_API_URL` | No | http://localhost:4200/api |

## Monitoring

### CloudWatch Logs (AWS)

```bash
aws logs tail /ecs/techstack --follow
```

### Prefect Server

Access UI at `http://localhost:4200` to view:
- Workflow execution history
- Task logs
- Performance metrics
- Flow state changes

## Health Checks

Test deployment:

```bash
# Local
uv run python -c "from src.analytics_flows import enhanced_analytics_flow; print('OK')"

# Docker
docker run techstack:latest uv run python -c "from src.analytics_flows import enhanced_analytics_flow; print('OK')"

# ECS
aws ecs describe-tasks --cluster default --tasks <task-arn>
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| OOM errors | Increase task memory (512MB → 1GB) |
| Email not sending | Verify AWS Secrets Manager values |
| API rate limits | Enable caching, reduce request frequency |
| Parquet file access | Check S3 bucket permissions |
