#!/usr/bin/env bash

# AgentEval Live Demo Setup Script
# ==================================
# Deploys AWS infrastructure for live demo testing
# Creates DynamoDB tables, S3 buckets, and EventBridge event bus

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${AGENTEVAL_STACK_NAME:-agenteval-live-demo}"
DEMO_TAG="live-demo"
PERSONA_MODEL="${AWS_BEDROCK_PERSONA_MODEL:-anthropic.claude-haiku-4-5-20251001-v1:0}"
REDTEAM_MODEL="${AWS_BEDROCK_REDTEAM_MODEL:-anthropic.claude-haiku-4-5-20251001-v1:0}"
JUDGE_MODEL="${AWS_BEDROCK_JUDGE_MODEL:-amazon.nova-pro-v1:0}"
PERSONA_FALLBACK_MODEL="${AWS_BEDROCK_PERSONA_FALLBACK_MODEL:-amazon.titan-text-lite-v1}"
REDTEAM_FALLBACK_MODEL="${AWS_BEDROCK_REDTEAM_FALLBACK_MODEL:-amazon.titan-text-lite-v1}"
JUDGE_FALLBACK_MODEL="${AWS_BEDROCK_JUDGE_FALLBACK_MODEL:-amazon.titan-text-express-v1}"
PERSONA_PROFILE_ARN="${AWS_BEDROCK_PERSONA_PROFILE_ARN:-}"
REDTEAM_PROFILE_ARN="${AWS_BEDROCK_REDTEAM_PROFILE_ARN:-}"
JUDGE_PROFILE_ARN="${AWS_BEDROCK_JUDGE_PROFILE_ARN:-}"
DEMO_TARGET_URL_VALUE="${DEMO_TARGET_URL:-https://postman-echo.com/post}"
DEMO_FALLBACK_TARGET_URL_VALUE="${DEMO_FALLBACK_TARGET_URL:-https://postman-echo.com/post}"
DEMO_PERSONA_MAX_TURNS_VALUE="${DEMO_PERSONA_MAX_TURNS:-3}"
DEMO_REDTEAM_MAX_TURNS_VALUE="${DEMO_REDTEAM_MAX_TURNS:-2}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
  echo -e "${BLUE}ℹ${NC} $*"
}

log_success() {
  echo -e "${GREEN}✓${NC} $*"
}

log_warning() {
  echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
  echo -e "${RED}✗${NC} $*"
}

usage() {
  cat <<'USAGE'
Usage: scripts/setup-live-demo.sh [options]

Options:
  --region <aws-region>    AWS region (default: us-east-1 or $AWS_REGION)
  --stack-name <name>      Stack name (default: agenteval-live-demo)
  --skip-bedrock          Skip Bedrock model verification
  -h, --help              Show this help message

Example:
  scripts/setup-live-demo.sh --region us-east-1
USAGE
}

SKIP_BEDROCK=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)
      REGION="$2"; shift 2 ;;
    --stack-name)
      STACK_NAME="$2"; shift 2 ;;
    --skip-bedrock)
      SKIP_BEDROCK=true; shift 1 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1 ;;
  esac
done

echo ""
echo "================================================"
echo "  AgentEval Live Demo Setup"
echo "================================================"
echo ""
echo "Region: $REGION"
echo "Stack Name: $STACK_NAME"
echo ""

# Check AWS CLI
log_info "Checking AWS CLI..."
if ! command -v aws >/dev/null 2>&1; then
  log_error "AWS CLI not installed"
  exit 1
fi

if ! aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1; then
  log_error "AWS CLI not configured or credentials invalid"
  exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
log_success "AWS CLI configured (Account: $ACCOUNT_ID)"

# Create DynamoDB tables
log_info "Creating DynamoDB tables..."

create_table_if_not_exists() {
  local table_name=$1
  local pk_name=$2
  local sk_name=$3

  if aws dynamodb describe-table --table-name "$table_name" --region "$REGION" >/dev/null 2>&1; then
    log_warning "Table $table_name already exists"
  else
    log_info "Creating table: $table_name"
    aws dynamodb create-table \
      --table-name "$table_name" \
      --attribute-definitions \
        AttributeName="$pk_name",AttributeType=S \
        AttributeName="$sk_name",AttributeType=S \
      --key-schema \
        AttributeName="$pk_name",KeyType=HASH \
        AttributeName="$sk_name",KeyType=RANGE \
      --billing-mode PAY_PER_REQUEST \
      --tags Key=Project,Value=AgentEval Key=Environment,Value=$DEMO_TAG Key=ManagedBy,Value=setup-script \
      --region "$REGION" \
      >/dev/null

    # Wait for table to be active
    log_info "Waiting for table $table_name to be active..."
    aws dynamodb wait table-exists --table-name "$table_name" --region "$REGION"
    log_success "Table $table_name created and active"
  fi
}

create_table_if_not_exists "agenteval-campaigns" "PK" "SK"
create_table_if_not_exists "agenteval-turns" "PK" "SK"
create_table_if_not_exists "agenteval-evaluations" "PK" "SK"
create_table_if_not_exists "agenteval-attack-knowledge" "PK" "SK"

# Create S3 buckets
log_info "Creating S3 buckets..."

create_bucket_if_not_exists() {
  local bucket_name=$1

  if aws s3 ls "s3://$bucket_name" --region "$REGION" 2>/dev/null; then
    log_warning "Bucket $bucket_name already exists"
  else
    log_info "Creating bucket: $bucket_name"

    if [ "$REGION" = "us-east-1" ]; then
      aws s3 mb "s3://$bucket_name" --region "$REGION"
    else
      aws s3 mb "s3://$bucket_name" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"
    fi

    # Add tags
    aws s3api put-bucket-tagging \
      --bucket "$bucket_name" \
      --tagging "TagSet=[{Key=Project,Value=AgentEval},{Key=Environment,Value=$DEMO_TAG},{Key=ManagedBy,Value=setup-script}]" \
      --region "$REGION"

    log_success "Bucket $bucket_name created"
  fi
}

RESULTS_BUCKET="agenteval-results-${ACCOUNT_ID}"
REPORTS_BUCKET="agenteval-reports-${ACCOUNT_ID}"

create_bucket_if_not_exists "$RESULTS_BUCKET"
create_bucket_if_not_exists "$REPORTS_BUCKET"

# Create EventBridge event bus
log_info "Creating EventBridge event bus..."

BUS_NAME="agenteval"

if aws events describe-event-bus --name "$BUS_NAME" --region "$REGION" >/dev/null 2>&1; then
  log_warning "Event bus $BUS_NAME already exists"
else
  log_info "Creating event bus: $BUS_NAME"
  aws events create-event-bus \
    --name "$BUS_NAME" \
    --tags Key=Project,Value=AgentEval Key=Environment,Value=$DEMO_TAG Key=ManagedBy,Value=setup-script \
    --region "$REGION" \
    >/dev/null
  log_success "Event bus $BUS_NAME created"
fi

# Verify Bedrock model access
if [ "$SKIP_BEDROCK" = "false" ]; then
  log_info "Verifying Bedrock model access..."

REQUIRED_MODELS=("$PERSONA_MODEL" "$JUDGE_MODEL")
if [ -n "$PERSONA_FALLBACK_MODEL" ]; then
  REQUIRED_MODELS+=("$PERSONA_FALLBACK_MODEL")
fi
if [ -n "$JUDGE_FALLBACK_MODEL" ] && [[ "$JUDGE_FALLBACK_MODEL" != "$PERSONA_FALLBACK_MODEL" ]]; then
  REQUIRED_MODELS+=("$JUDGE_FALLBACK_MODEL")
fi

  ACCESSIBLE_COUNT=0
  for model in "${REQUIRED_MODELS[@]}"; do
    if aws bedrock get-foundation-model \
      --model-identifier "$model" \
      --region "$REGION" >/dev/null 2>&1; then
      log_success "Bedrock model accessible: $model"
      ((ACCESSIBLE_COUNT++))
    else
      log_warning "Bedrock model NOT accessible: $model"
      log_warning "  → Enable this model in the AWS Bedrock console"
    fi
  done

  if [ $ACCESSIBLE_COUNT -eq ${#REQUIRED_MODELS[@]} ]; then
    log_success "All Bedrock models are accessible"
  else
    log_warning "Some Bedrock models are not accessible ($ACCESSIBLE_COUNT/${#REQUIRED_MODELS[@]})"
    log_warning "  → Demo will use mocked responses for unavailable models"
  fi
else
  log_info "Skipping Bedrock verification (--skip-bedrock)"
fi

ENV_FILE=".env.live-demo"
if [ -f "$ENV_FILE" ]; then
  log_info "Existing configuration preserved: $ENV_FILE"
else
  log_warning "$ENV_FILE not found – create one before running the live demo."
  cat <<EOF

Suggested configuration (copy/paste into $ENV_FILE and adjust as needed):

# AgentEval Live Demo Environment Configuration

# AWS Configuration
AWS_REGION=$REGION
AWS_PROFILE=${AWS_PROFILE:-default}

# DynamoDB Tables
AWS_DYNAMODB_CAMPAIGNS_TABLE=agenteval-campaigns
AWS_DYNAMODB_TURNS_TABLE=agenteval-turns
AWS_DYNAMODB_EVALUATIONS_TABLE=agenteval-evaluations
AWS_DYNAMODB_KNOWLEDGE_BASE_TABLE=agenteval-attack-knowledge

# S3 Buckets
AWS_S3_RESULTS_BUCKET=$RESULTS_BUCKET
AWS_S3_REPORTS_BUCKET=$REPORTS_BUCKET

# EventBridge
AWS_EVENTBRIDGE_BUS_NAME=$BUS_NAME

# Bedrock Models
AWS_BEDROCK_PERSONA_MODEL=$PERSONA_MODEL
AWS_BEDROCK_REDTEAM_MODEL=$REDTEAM_MODEL
AWS_BEDROCK_JUDGE_MODEL=$JUDGE_MODEL
AWS_BEDROCK_PERSONA_FALLBACK_MODEL=$PERSONA_FALLBACK_MODEL
AWS_BEDROCK_REDTEAM_FALLBACK_MODEL=$REDTEAM_FALLBACK_MODEL
AWS_BEDROCK_JUDGE_FALLBACK_MODEL=$JUDGE_FALLBACK_MODEL
AWS_BEDROCK_PERSONA_PROFILE_ARN=$PERSONA_PROFILE_ARN
AWS_BEDROCK_REDTEAM_PROFILE_ARN=$REDTEAM_PROFILE_ARN
AWS_BEDROCK_JUDGE_PROFILE_ARN=$JUDGE_PROFILE_ARN

# Application Settings
ENVIRONMENT=live-demo
LOG_LEVEL=INFO
ENABLE_XRAY_TRACING=true

# Demo configuration
DEMO_TARGET_URL=$DEMO_TARGET_URL_VALUE
DEMO_FALLBACK_TARGET_URL=$DEMO_FALLBACK_TARGET_URL_VALUE
DEMO_PERSONA_MAX_TURNS=$DEMO_PERSONA_MAX_TURNS_VALUE
DEMO_REDTEAM_MAX_TURNS=$DEMO_REDTEAM_MAX_TURNS_VALUE

# Demo Metadata
ACCOUNT_ID=$ACCOUNT_ID
STACK_NAME=$STACK_NAME
SETUP_TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

EOF
fi

echo ""
echo "================================================"
echo "  Setup Complete!"
echo "================================================"
echo ""
echo "Resources created:"
echo "  DynamoDB Tables: 4"
echo "  S3 Buckets: 2"
echo "  EventBridge Bus: 1"
echo ""
echo "Next steps:"
echo "  1. Populate .env.live-demo with the values above (or your preferred configuration)"
echo "  2. Run live demo: python demo_agenteval_live.py"
echo "  3. Clean up: scripts/teardown-live-demo.sh"
echo ""
echo "To check service status:"
echo "  scripts/check-aws-services.sh --region $REGION"
echo ""
