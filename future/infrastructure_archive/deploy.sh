#!/usr/bin/env bash
# AgentEval Deployment Script
# Automates the deployment of AgentEval to AWS ECS Fargate

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT_NAME="${ENVIRONMENT_NAME:-agenteval}"
AWS_REGION="${AWS_REGION:-us-east-1}"
ECR_REPOSITORY="${ECR_REPOSITORY:-agenteval}"
DESIRED_COUNT="${DESIRED_COUNT:-2}"
CONTAINER_CPU="${CONTAINER_CPU:-512}"
CONTAINER_MEMORY="${CONTAINER_MEMORY:-1024}"

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    if ! command_exists aws; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi

    if ! command_exists docker; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi

    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        print_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi

    print_info "Prerequisites check passed!"
}

# Get AWS account ID
get_account_id() {
    aws sts get-caller-identity --query Account --output text
}

# Create ECR repository if it doesn't exist
create_ecr_repository() {
    print_info "Creating ECR repository if not exists..."

    if aws ecr describe-repositories --repository-names "${ECR_REPOSITORY}" --region "${AWS_REGION}" >/dev/null 2>&1; then
        print_info "ECR repository already exists"
    else
        aws ecr create-repository \
            --repository-name "${ECR_REPOSITORY}" \
            --region "${AWS_REGION}" \
            --image-scanning-configuration scanOnPush=true \
            --tags Key=Project,Value=AgentEval Key=Environment,Value=production
        print_info "ECR repository created successfully"
    fi
}

# Build and push Docker image
build_and_push_image() {
    print_info "Building and pushing Docker image..."

    local account_id=$(get_account_id)
    local ecr_uri="${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}"

    # Login to ECR
    print_info "Logging in to ECR..."
    aws ecr get-login-password --region "${AWS_REGION}" | \
        docker login --username AWS --password-stdin "${ecr_uri}"

    # Build image
    print_info "Building Docker image..."
    docker build -t "${ECR_REPOSITORY}:latest" .

    # Tag image
    print_info "Tagging image..."
    docker tag "${ECR_REPOSITORY}:latest" "${ecr_uri}:latest"
    docker tag "${ECR_REPOSITORY}:latest" "${ecr_uri}:$(date +%Y%m%d-%H%M%S)"

    # Push image
    print_info "Pushing image to ECR..."
    docker push "${ecr_uri}:latest"
    docker push "${ecr_uri}:$(date +%Y%m%d-%H%M%S)"

    print_info "Docker image pushed successfully!"
    echo "${ecr_uri}:latest"
}

# Store secrets in Parameter Store
store_secrets() {
    print_info "Storing secrets in Parameter Store..."

    # Generate secure keys if they don't exist
    if ! aws ssm get-parameter --name "/agenteval/production/api-key" --region "${AWS_REGION}" >/dev/null 2>&1; then
        local api_key=$(openssl rand -base64 32)
        aws ssm put-parameter \
            --name "/agenteval/production/api-key" \
            --type SecureString \
            --value "${api_key}" \
            --region "${AWS_REGION}" \
            --tags Key=Project,Value=AgentEval Key=Environment,Value=production
        print_info "API key stored in Parameter Store"
        print_warn "API Key: ${api_key}"
        print_warn "SAVE THIS KEY - IT WILL NOT BE SHOWN AGAIN!"
    else
        print_info "API key already exists in Parameter Store"
    fi

    if ! aws ssm get-parameter --name "/agenteval/production/secret-key" --region "${AWS_REGION}" >/dev/null 2>&1; then
        local secret_key=$(openssl rand -base64 64)
        aws ssm put-parameter \
            --name "/agenteval/production/secret-key" \
            --type SecureString \
            --value "${secret_key}" \
            --region "${AWS_REGION}" \
            --tags Key=Project,Value=AgentEval Key=Environment,Value=production
        print_info "Secret key stored in Parameter Store"
    else
        print_info "Secret key already exists in Parameter Store"
    fi
}

# Deploy network stack
deploy_network() {
    print_info "Deploying network infrastructure..."

    if aws cloudformation describe-stacks --stack-name "${ENVIRONMENT_NAME}-network" --region "${AWS_REGION}" >/dev/null 2>&1; then
        print_info "Network stack already exists, updating..."
        aws cloudformation update-stack \
            --stack-name "${ENVIRONMENT_NAME}-network" \
            --template-body file://infrastructure/cloudformation/network.yaml \
            --parameters ParameterKey=EnvironmentName,ParameterValue="${ENVIRONMENT_NAME}" \
            --capabilities CAPABILITY_IAM \
            --region "${AWS_REGION}" || print_warn "No changes to network stack"
    else
        aws cloudformation create-stack \
            --stack-name "${ENVIRONMENT_NAME}-network" \
            --template-body file://infrastructure/cloudformation/network.yaml \
            --parameters ParameterKey=EnvironmentName,ParameterValue="${ENVIRONMENT_NAME}" \
            --capabilities CAPABILITY_IAM \
            --region "${AWS_REGION}" \
            --tags Key=Project,Value=AgentEval Key=Environment,Value=production

        print_info "Waiting for network stack creation..."
        aws cloudformation wait stack-create-complete \
            --stack-name "${ENVIRONMENT_NAME}-network" \
            --region "${AWS_REGION}"
    fi

    print_info "Network stack deployed successfully!"
}

# Provision AWS resources (DynamoDB, S3, etc.)
provision_resources() {
    print_info "Provisioning AWS resources (DynamoDB, S3, EventBridge)..."

    if [ -f "./scripts/setup-live-demo.sh" ]; then
        ./scripts/setup-live-demo.sh --region "${AWS_REGION}"
        print_info "AWS resources provisioned successfully!"
    else
        print_warn "setup-live-demo.sh not found, skipping resource provisioning"
    fi
}

# Deploy ECS stack
deploy_ecs() {
    print_info "Deploying ECS infrastructure..."

    local account_id=$(get_account_id)
    local container_image="${account_id}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest"

    if aws cloudformation describe-stacks --stack-name "${ENVIRONMENT_NAME}-ecs" --region "${AWS_REGION}" >/dev/null 2>&1; then
        print_info "ECS stack already exists, updating..."
        aws cloudformation update-stack \
            --stack-name "${ENVIRONMENT_NAME}-ecs" \
            --template-body file://infrastructure/cloudformation/ecs-cluster.yaml \
            --parameters \
                ParameterKey=EnvironmentName,ParameterValue="${ENVIRONMENT_NAME}" \
                ParameterKey=ContainerImage,ParameterValue="${container_image}" \
                ParameterKey=DesiredCount,ParameterValue="${DESIRED_COUNT}" \
                ParameterKey=ContainerCpu,ParameterValue="${CONTAINER_CPU}" \
                ParameterKey=ContainerMemory,ParameterValue="${CONTAINER_MEMORY}" \
            --capabilities CAPABILITY_IAM \
            --region "${AWS_REGION}" || print_warn "No changes to ECS stack"
    else
        aws cloudformation create-stack \
            --stack-name "${ENVIRONMENT_NAME}-ecs" \
            --template-body file://infrastructure/cloudformation/ecs-cluster.yaml \
            --parameters \
                ParameterKey=EnvironmentName,ParameterValue="${ENVIRONMENT_NAME}" \
                ParameterKey=ContainerImage,ParameterValue="${container_image}" \
                ParameterKey=DesiredCount,ParameterValue="${DESIRED_COUNT}" \
                ParameterKey=ContainerCpu,ParameterValue="${CONTAINER_CPU}" \
                ParameterKey=ContainerMemory,ParameterValue="${CONTAINER_MEMORY}" \
            --capabilities CAPABILITY_IAM \
            --region "${AWS_REGION}" \
            --tags Key=Project,Value=AgentEval Key=Environment,Value=production

        print_info "Waiting for ECS stack creation (this may take 5-10 minutes)..."
        aws cloudformation wait stack-create-complete \
            --stack-name "${ENVIRONMENT_NAME}-ecs" \
            --region "${AWS_REGION}"
    fi

    print_info "ECS stack deployed successfully!"
}

# Get deployment outputs
get_outputs() {
    print_info "Retrieving deployment outputs..."

    local alb_dns=$(aws cloudformation describe-stacks \
        --stack-name "${ENVIRONMENT_NAME}-ecs" \
        --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
        --output text \
        --region "${AWS_REGION}")

    echo ""
    print_info "=========================================="
    print_info "Deployment Complete!"
    print_info "=========================================="
    echo ""
    print_info "AgentEval URL: http://${alb_dns}"
    print_info "Health Check: http://${alb_dns}/health"
    echo ""
    print_info "To test the deployment:"
    echo "  curl http://${alb_dns}/health"
    echo ""
    print_info "View logs:"
    echo "  aws logs tail /ecs/${ENVIRONMENT_NAME} --follow --region ${AWS_REGION}"
    echo ""
}

# Main deployment function
main() {
    echo "=========================================="
    echo "AgentEval AWS Deployment"
    echo "=========================================="
    echo ""
    echo "Environment: ${ENVIRONMENT_NAME}"
    echo "Region: ${AWS_REGION}"
    echo "ECR Repository: ${ECR_REPOSITORY}"
    echo ""

    check_prerequisites
    create_ecr_repository
    build_and_push_image
    store_secrets
    deploy_network
    provision_resources
    deploy_ecs
    get_outputs
}

# Run main function
main "$@"
