# AgentEval AWS Deployment Guide

This guide provides step-by-step instructions for deploying AgentEval to AWS using ECS Fargate.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud                             │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                      VPC                                │ │
│  │                                                          │ │
│  │  ┌──────────────┐         ┌──────────────┐            │ │
│  │  │ Public Subnet│         │ Public Subnet│            │ │
│  │  │     AZ-1     │         │     AZ-2     │            │ │
│  │  │              │         │              │            │ │
│  │  │ ┌──────────┐ │         │ ┌──────────┐ │            │ │
│  │  │ │   ALB    │◄├─────────┤►│   NAT    │ │            │ │
│  │  │ └────┬─────┘ │         │ └──────────┘ │            │ │
│  │  └──────┼────────┘         └──────────────┘            │ │
│  │         │                                               │ │
│  │  ┌──────▼───────┐         ┌──────────────┐            │ │
│  │  │Private Subnet│         │Private Subnet│            │ │
│  │  │     AZ-1     │         │     AZ-2     │            │ │
│  │  │              │         │              │            │ │
│  │  │ ┌──────────┐ │         │ ┌──────────┐ │            │ │
│  │  │ │ECS Fargate│ │         │ │ECS Fargate│ │            │ │
│  │  │ │   Task   │ │         │ │   Task   │ │            │ │
│  │  │ └────┬─────┘ │         │ └────┬─────┘ │            │ │
│  │  └──────┼────────┘         └──────┼───────┘            │ │
│  │         │                          │                    │ │
│  └─────────┼──────────────────────────┼────────────────────┘ │
│            │                          │                      │
│       ┌────▼───────────────────────────▼──────┐             │
│       │      AWS Services (via VPC Endpoints)  │             │
│       │  ┌─────────┐ ┌──────────┐ ┌─────────┐ │             │
│       │  │ DynamoDB│ │    S3    │ │ Bedrock │ │             │
│       │  └─────────┘ └──────────┘ └─────────┘ │             │
│       │  ┌─────────┐ ┌──────────┐             │             │
│       │  │  X-Ray  │ │EventBridge│            │             │
│       │  └─────────┘ └──────────┘             │             │
│       └─────────────────────────────────────────┘             │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. AWS Account Setup

- AWS Account with appropriate permissions
- AWS CLI configured with credentials
- Docker installed locally
- Git installed

### 2. Required AWS Services Access

- Amazon ECS (Fargate)
- Amazon ECR
- Application Load Balancer
- VPC with public/private subnets
- Bedrock (Claude Haiku 4.5, Amazon Nova Pro)
- DynamoDB
- S3
- EventBridge
- X-Ray

### 3. IAM Permissions Required

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "ec2:*",
        "ecs:*",
        "ecr:*",
        "elasticloadbalancing:*",
        "iam:*",
        "logs:*",
        "ssm:*",
        "bedrock:*",
        "dynamodb:*",
        "s3:*",
        "events:*",
        "xray:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Deployment Steps

### Step 1: Build and Push Docker Image

```bash
# Set your AWS account ID and region
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1
export ECR_REPOSITORY=agenteval

# Create ECR repository
aws ecr create-repository \
    --repository-name ${ECR_REPOSITORY} \
    --region ${AWS_REGION} \
    --image-scanning-configuration scanOnPush=true

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | \
    docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Build Docker image
docker build -t ${ECR_REPOSITORY}:latest .

# Tag image for ECR
docker tag ${ECR_REPOSITORY}:latest \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest

# Push to ECR
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest
```

### Step 2: Store Secrets in Parameter Store

```bash
# Generate secure API key and secret key
export API_KEY=$(openssl rand -base64 32)
export SECRET_KEY=$(openssl rand -base64 64)

# Store in SSM Parameter Store
aws ssm put-parameter \
    --name /agenteval/production/api-key \
    --type SecureString \
    --value "${API_KEY}" \
    --region ${AWS_REGION}

aws ssm put-parameter \
    --name /agenteval/production/secret-key \
    --type SecureString \
    --value "${SECRET_KEY}" \
    --region ${AWS_REGION}
```

### Step 3: Deploy Network Infrastructure

```bash
# Deploy VPC and networking
aws cloudformation create-stack \
    --stack-name agenteval-network \
    --template-body file://infrastructure/cloudformation/network.yaml \
    --parameters ParameterKey=EnvironmentName,ParameterValue=agenteval \
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION}

# Wait for stack creation
aws cloudformation wait stack-create-complete \
    --stack-name agenteval-network \
    --region ${AWS_REGION}

echo "Network stack created successfully!"
```

### Step 4: Provision Required AWS Resources

```bash
# Run the setup script to create DynamoDB tables, S3 buckets, etc.
./scripts/setup-live-demo.sh --region ${AWS_REGION}
```

### Step 5: Deploy ECS Cluster and Services

```bash
# Deploy ECS infrastructure
aws cloudformation create-stack \
    --stack-name agenteval-ecs \
    --template-body file://infrastructure/cloudformation/ecs-cluster.yaml \
    --parameters \
        ParameterKey=EnvironmentName,ParameterValue=agenteval \
        ParameterKey=ContainerImage,ParameterValue=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest \
        ParameterKey=DesiredCount,ParameterValue=2 \
        ParameterKey=ContainerCpu,ParameterValue=512 \
        ParameterKey=ContainerMemory,ParameterValue=1024 \
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION}

# Wait for stack creation (this may take 5-10 minutes)
aws cloudformation wait stack-create-complete \
    --stack-name agenteval-ecs \
    --region ${AWS_REGION}

echo "ECS stack created successfully!"
```

### Step 6: Get Load Balancer URL

```bash
# Get the ALB DNS name
export ALB_DNS=$(aws cloudformation describe-stacks \
    --stack-name agenteval-ecs \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text \
    --region ${AWS_REGION})

echo "AgentEval is now accessible at: http://${ALB_DNS}"
```

### Step 7: Verify Deployment

```bash
# Health check
curl http://${ALB_DNS}/health

# API info
curl http://${ALB_DNS}/

# List campaigns (requires API key)
curl -H "X-API-Key: ${API_KEY}" http://${ALB_DNS}/campaigns
```

## Post-Deployment Configuration

### 1. Configure DNS (Optional)

```bash
# If you have a domain, create a Route 53 record pointing to the ALB
aws route53 change-resource-record-sets \
    --hosted-zone-id YOUR_HOSTED_ZONE_ID \
    --change-batch '{
      "Changes": [{
        "Action": "CREATE",
        "ResourceRecordSet": {
          "Name": "agenteval.yourdomain.com",
          "Type": "CNAME",
          "TTL": 300,
          "ResourceRecords": [{"Value": "'${ALB_DNS}'"}]
        }
      }]
    }'
```

### 2. Enable HTTPS (Recommended for Production)

```bash
# Request SSL certificate from ACM
aws acm request-certificate \
    --domain-name agenteval.yourdomain.com \
    --validation-method DNS \
    --region ${AWS_REGION}

# Update ALB listener to use HTTPS (after certificate validation)
# This requires updating the CloudFormation template
```

### 3. Configure CloudWatch Alarms

```bash
# Create alarms for monitoring
aws cloudwatch put-metric-alarm \
    --alarm-name agenteval-high-cpu \
    --alarm-description "Alert when CPU exceeds 80%" \
    --metric-name CPUUtilization \
    --namespace AWS/ECS \
    --statistic Average \
    --period 300 \
    --threshold 80 \
    --comparison-operator GreaterThanThreshold \
    --evaluation-periods 2 \
    --region ${AWS_REGION}
```

## Monitoring and Maintenance

### View Logs

```bash
# View ECS service logs
aws logs tail /ecs/agenteval --follow --region ${AWS_REGION}
```

### Scale Service

```bash
# Update desired task count
aws ecs update-service \
    --cluster agenteval-cluster \
    --service agenteval-service \
    --desired-count 5 \
    --region ${AWS_REGION}
```

### Update Application

```bash
# Build and push new image
docker build -t ${ECR_REPOSITORY}:v2.0.0 .
docker tag ${ECR_REPOSITORY}:v2.0.0 \
    ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:v2.0.0
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:v2.0.0

# Update service to use new image
aws cloudformation update-stack \
    --stack-name agenteval-ecs \
    --use-previous-template \
    --parameters \
        ParameterKey=ContainerImage,ParameterValue=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:v2.0.0 \
    --capabilities CAPABILITY_IAM \
    --region ${AWS_REGION}
```

## Teardown

### Remove All Resources

```bash
# Delete ECS stack
aws cloudformation delete-stack \
    --stack-name agenteval-ecs \
    --region ${AWS_REGION}

# Wait for deletion
aws cloudformation wait stack-delete-complete \
    --stack-name agenteval-ecs \
    --region ${AWS_REGION}

# Delete network stack
aws cloudformation delete-stack \
    --stack-name agenteval-network \
    --region ${AWS_REGION}

aws cloudformation wait stack-delete-complete \
    --stack-name agenteval-network \
    --region ${AWS_REGION}

# Clean up AWS resources
./scripts/teardown-live-demo.sh --region ${AWS_REGION} --force

# Delete ECR repository
aws ecr delete-repository \
    --repository-name ${ECR_REPOSITORY} \
    --force \
    --region ${AWS_REGION}

# Delete SSM parameters
aws ssm delete-parameter \
    --name /agenteval/production/api-key \
    --region ${AWS_REGION}

aws ssm delete-parameter \
    --name /agenteval/production/secret-key \
    --region ${AWS_REGION}
```

## Cost Estimation

### Monthly Cost Breakdown (us-east-1)

| Service                       | Configuration                     | Estimated Cost  |
| ----------------------------- | --------------------------------- | --------------- |
| ECS Fargate                   | 2 tasks (0.5 vCPU, 1GB RAM, 24/7) | $30             |
| Application Load Balancer     | 1 ALB                             | $23             |
| NAT Gateway                   | 2 NAT Gateways                    | $64             |
| CloudWatch Logs               | 10 GB/month                       | $5              |
| DynamoDB                      | On-demand, light usage            | $5              |
| S3                            | 10 GB storage                     | $0.23           |
| Bedrock API                   | Pay per use                       | Variable        |
| Data Transfer                 | 10 GB outbound                    | $0.90           |
| **Total (excluding Bedrock)** |                                   | **~$128/month** |

> **Note:** Bedrock costs depend on usage. Estimate $0.03-0.30 per 1000 tokens for Claude/Nova
> models.

### Cost Optimization Tips

1. Use Fargate Spot for non-production workloads (70% savings)
1. Enable S3 Lifecycle policies to archive old data
1. Use DynamoDB on-demand pricing for unpredictable workloads
1. Implement caching to reduce Bedrock API calls
1. Use single NAT Gateway for development environments

## Troubleshooting

### Service Won't Start

```bash
# Check task logs
aws ecs describe-tasks \
    --cluster agenteval-cluster \
    --tasks $(aws ecs list-tasks --cluster agenteval-cluster --service agenteval-service --query 'taskArns[0]' --output text) \
    --region ${AWS_REGION}

# Check service events
aws ecs describe-services \
    --cluster agenteval-cluster \
    --services agenteval-service \
    --region ${AWS_REGION} \
    --query 'services[0].events[:5]'
```

### High CPU/Memory Usage

```bash
# View metrics
aws cloudwatch get-metric-statistics \
    --namespace AWS/ECS \
    --metric-name CPUUtilization \
    --dimensions Name=ServiceName,Value=agenteval-service Name=ClusterName,Value=agenteval-cluster \
    --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 300 \
    --statistics Average \
    --region ${AWS_REGION}
```

### Connection Issues

- Verify security group rules allow traffic
- Check target group health checks
- Ensure tasks are in private subnets with NAT Gateway access
- Verify IAM roles have correct permissions

## Support

For issues or questions:

- GitHub Issues: https://github.com/issacj-17/AgentEval/issues
- Email: issac.jose@example.com
- Documentation: https://agenteval.dev/docs
