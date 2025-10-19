#!/usr/bin/env bash

# AgentEval AWS Services Health Check
# ------------------------------------
# Verifies all AWS resources are running/available and checks for cost-incurring services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${AGENTEVAL_STACK_NAME:-agenteval}"
QUIET_MODE=false
JSON_OUTPUT=false

usage() {
  cat <<'USAGE'
Usage: scripts/check-aws-services.sh [options]

Options:
  --region <aws-region>    AWS region to check (default: us-east-1 or $AWS_REGION)
  --stack-name <name>      CloudFormation stack name (default: agenteval)
  --quiet                  Only show errors and warnings
  --json                   Output results in JSON format
  -h, --help              Show this help message

Examples:
  scripts/check-aws-services.sh --region us-east-1
  scripts/check-aws-services.sh --quiet
  scripts/check-aws-services.sh --json | jq .
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)
      REGION="$2"; shift 2 ;;
    --stack-name)
      STACK_NAME="$2"; shift 2 ;;
    --quiet)
      QUIET_MODE=true; shift 1 ;;
    --json)
      JSON_OUTPUT=true; shift 1 ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1 ;;
  esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# JSON output builder
JSON_RESULTS='{}'

log_info() {
  if [[ "$QUIET_MODE" == "false" && "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${BLUE}ℹ${NC} $*"
  fi
}

log_success() {
  if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${GREEN}✓${NC} $*"
  fi
}

log_warning() {
  if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${YELLOW}⚠${NC} $*"
  fi
}

log_error() {
  if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo -e "${RED}✗${NC} $*"
  fi
}

add_json_result() {
  local service=$1
  local status=$2
  local details=$3
  JSON_RESULTS=$(echo "$JSON_RESULTS" | jq --arg svc "$service" --arg st "$status" --arg det "$details" \
    '.[$svc] = {status: $st, details: $det}')
}

check_aws_cli() {
  if ! command -v aws >/dev/null 2>&1; then
    log_error "AWS CLI not installed"
    exit 1
  fi

  if ! aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1; then
    log_error "AWS CLI not configured or credentials invalid"
    exit 1
  fi

  ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
  CALLER_ARN=$(aws sts get-caller-identity --query Arn --output text 2>/dev/null)

  log_success "AWS CLI configured (Account: $ACCOUNT_ID)"
  add_json_result "aws_cli" "ok" "Account: $ACCOUNT_ID"
}

check_cloudformation() {
  log_info "Checking CloudFormation stack: $STACK_NAME"

  if ! STACK_STATUS=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].StackStatus' \
    --output text 2>/dev/null); then
    log_warning "Stack '$STACK_NAME' not found"
    add_json_result "cloudformation" "not_found" "Stack not deployed"
    return 0
  fi

  case "$STACK_STATUS" in
    CREATE_COMPLETE|UPDATE_COMPLETE|UPDATE_ROLLBACK_COMPLETE)
      log_success "CloudFormation stack: $STACK_STATUS"
      add_json_result "cloudformation" "ok" "$STACK_STATUS"
      ;;
    *IN_PROGRESS)
      log_warning "CloudFormation stack: $STACK_STATUS"
      add_json_result "cloudformation" "in_progress" "$STACK_STATUS"
      ;;
    *FAILED|*ROLLBACK*)
      log_error "CloudFormation stack: $STACK_STATUS"
      add_json_result "cloudformation" "error" "$STACK_STATUS"
      ;;
    *)
      log_warning "CloudFormation stack: $STACK_STATUS"
      add_json_result "cloudformation" "unknown" "$STACK_STATUS"
      ;;
  esac
}

check_dynamodb() {
  log_info "Checking DynamoDB tables"

  EXPECTED_TABLES=(
    "agenteval-campaigns"
    "agenteval-turns"
    "agenteval-evaluations"
    "agenteval-attack-knowledge"
  )

  local found=0
  local missing=0
  local table_details=""

  for table in "${EXPECTED_TABLES[@]}"; do
    if TABLE_STATUS=$(aws dynamodb describe-table \
      --table-name "$table" \
      --region "$REGION" \
      --query 'Table.[TableStatus,BillingModeSummary.BillingMode,TableSizeBytes]' \
      --output text 2>/dev/null); then
      ((found++))
      read -r status billing size <<< "$TABLE_STATUS"
      size_mb=$((size / 1024 / 1024))
      log_success "Table $table: $status ($billing, ${size_mb}MB)"
      table_details="$table_details$table($status,$billing,${size_mb}MB); "
    else
      ((missing++))
      log_warning "Table $table: NOT FOUND"
      table_details="${table_details}$table(missing); "
    fi
  done

  if [[ $found -gt 0 ]]; then
    add_json_result "dynamodb" "ok" "$found tables found: $table_details"
  else
    add_json_result "dynamodb" "not_found" "No tables found"
  fi

  log_info "DynamoDB: $found found, $missing missing"
}

check_s3() {
  log_info "Checking S3 buckets"

  EXPECTED_BUCKETS=(
    "agenteval-results"
    "agenteval-reports"
  )

  local found=0
  local missing=0
  local bucket_details=""

  for bucket_prefix in "${EXPECTED_BUCKETS[@]}"; do
    # Check with and without account ID suffix
    for bucket in "${bucket_prefix}" "${bucket_prefix}-${ACCOUNT_ID}"; do
      if BUCKET_INFO=$(aws s3 ls "s3://$bucket" --region "$REGION" 2>/dev/null); then
        OBJECT_COUNT=$(aws s3 ls "s3://$bucket" --recursive --region "$REGION" 2>/dev/null | wc -l | tr -d ' ')
        SIZE=$(aws s3 ls "s3://$bucket" --recursive --summarize --region "$REGION" 2>/dev/null | grep "Total Size" | awk '{print $3}')
        SIZE_MB=$((SIZE / 1024 / 1024))
        ((found++))
        log_success "Bucket $bucket: ${OBJECT_COUNT} objects, ${SIZE_MB}MB"
        bucket_details="${bucket_details}$bucket(${OBJECT_COUNT}obj,${SIZE_MB}MB); "
        break
      fi
    done
    if [[ $found -eq 0 ]]; then
      ((missing++))
      log_warning "Bucket $bucket_prefix*: NOT FOUND"
      bucket_details="${bucket_details}${bucket_prefix}(missing); "
    fi
  done

  if [[ $found -gt 0 ]]; then
    add_json_result "s3" "ok" "$found buckets: $bucket_details"
  else
    add_json_result "s3" "not_found" "No buckets found"
  fi
}

check_eventbridge() {
  log_info "Checking EventBridge event bus"

  BUS_NAME="agenteval"

  if BUS_ARN=$(aws events describe-event-bus \
    --name "$BUS_NAME" \
    --region "$REGION" \
    --query 'Arn' \
    --output text 2>/dev/null); then
    log_success "EventBridge bus: $BUS_NAME"
    add_json_result "eventbridge" "ok" "$BUS_ARN"

    # Check for active rules
    RULE_COUNT=$(aws events list-rules \
      --event-bus-name "$BUS_NAME" \
      --region "$REGION" \
      --query 'length(Rules)' \
      --output text 2>/dev/null || echo "0")
    log_info "  Active rules: $RULE_COUNT"
  else
    log_warning "EventBridge bus '$BUS_NAME': NOT FOUND"
    add_json_result "eventbridge" "not_found" "Event bus not created"
  fi
}

check_ecs() {
  log_info "Checking ECS cluster and services"

  CLUSTER_NAME="agenteval-cluster"

  if CLUSTER_STATUS=$(aws ecs describe-clusters \
    --clusters "$CLUSTER_NAME" \
    --region "$REGION" \
    --query 'clusters[0].[status,runningTasksCount,activeServicesCount]' \
    --output text 2>/dev/null); then
    read -r status running_tasks active_services <<< "$CLUSTER_STATUS"

    if [[ "$status" == "ACTIVE" ]]; then
      log_success "ECS cluster: $CLUSTER_NAME ($status)"
      log_info "  Running tasks: $running_tasks"
      log_info "  Active services: $active_services"
      add_json_result "ecs" "ok" "Cluster: $status, Tasks: $running_tasks, Services: $active_services"

      if [[ $running_tasks -gt 0 ]]; then
        log_warning "  ⚠ $running_tasks task(s) running (incurring costs)"
      fi
    else
      log_warning "ECS cluster: $CLUSTER_NAME ($status)"
      add_json_result "ecs" "warning" "Cluster status: $status"
    fi
  else
    log_warning "ECS cluster '$CLUSTER_NAME': NOT FOUND"
    add_json_result "ecs" "not_found" "Cluster not created"
  fi
}

check_ec2() {
  log_info "Checking EC2 instances"

  RUNNING_INSTANCES=$(aws ec2 describe-instances \
    --region "$REGION" \
    --filters "Name=instance-state-name,Values=running" \
    --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,State.Name,Tags[?Key==`Name`].Value|[0]]' \
    --output text 2>/dev/null || true)

  if [[ -n "$RUNNING_INSTANCES" ]]; then
    INSTANCE_COUNT=$(echo "$RUNNING_INSTANCES" | wc -l | tr -d ' ')
    log_warning "$INSTANCE_COUNT EC2 instance(s) running (incurring costs)"
    echo "$RUNNING_INSTANCES" | while read -r id type state name; do
      log_info "  $id ($type) - $name"
    done
    add_json_result "ec2" "warning" "$INSTANCE_COUNT instances running"
  else
    log_success "EC2: No running instances"
    add_json_result "ec2" "ok" "No instances running"
  fi
}

check_bedrock() {
  log_info "Checking Bedrock model access"

  local -a REQUIRED_MODELS=()

  PERSONA_MODEL="${AWS_BEDROCK_PERSONA_MODEL:-anthropic.claude-haiku-4-5-20251001-v1:0}"
  REDTEAM_MODEL="${AWS_BEDROCK_REDTEAM_MODEL:-anthropic.claude-haiku-4-5-20251001-v1:0}"
  JUDGE_MODEL="${AWS_BEDROCK_JUDGE_MODEL:-amazon.nova-pro-v1:0}"
  PERSONA_FALLBACK="${AWS_BEDROCK_PERSONA_FALLBACK_MODEL:-amazon.titan-text-lite-v1}"
  REDTEAM_FALLBACK="${AWS_BEDROCK_REDTEAM_FALLBACK_MODEL:-amazon.titan-text-lite-v1}"
  JUDGE_FALLBACK="${AWS_BEDROCK_JUDGE_FALLBACK_MODEL:-amazon.titan-text-express-v1}"

  add_unique_model() {
    local model_value="$1"
    if [[ -z "$model_value" ]]; then
      return
    fi
    for existing in "${REQUIRED_MODELS[@]:-}"; do
      if [[ "$existing" == "$model_value" ]]; then
        return
      fi
    done
    REQUIRED_MODELS+=("$model_value")
  }

  add_unique_model "$PERSONA_MODEL"
  add_unique_model "$REDTEAM_MODEL"
  add_unique_model "$JUDGE_MODEL"
  add_unique_model "$PERSONA_FALLBACK"
  add_unique_model "$REDTEAM_FALLBACK"
  add_unique_model "$JUDGE_FALLBACK"

  local accessible=0
  local inaccessible=0

  for model in "${REQUIRED_MODELS[@]:-}"; do
    if aws bedrock get-foundation-model \
      --model-identifier "$model" \
      --region "$REGION" >/dev/null 2>&1; then
      ((accessible++))
      log_success "Bedrock model accessible: $model"
    else
      ((inaccessible++))
      log_warning "Bedrock model NOT accessible: $model"
    fi
  done

  local total_models=${#REQUIRED_MODELS[@]}

  if [[ $total_models -eq 0 ]]; then
    log_warning "No Bedrock models configured via environment."
    add_json_result "bedrock" "not_configured" "No models defined in environment"
    return
  fi

  if [[ $accessible -eq $total_models ]]; then
    add_json_result "bedrock" "ok" "All $accessible models accessible"
  elif [[ $accessible -gt 0 ]]; then
    add_json_result "bedrock" "partial" "$accessible/$total_models models accessible"
  else
    add_json_result "bedrock" "not_configured" "No models accessible - enable in console"
  fi
}

check_xray() {
  log_info "Checking X-Ray traces"

  # Check for traces in the last hour
  START_TIME=$(date -u -v-1H '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || echo "2024-01-01T00:00:00")
  END_TIME=$(date -u '+%Y-%m-%dT%H:%M:%S')

  if TRACE_COUNT=$(aws xray get-trace-summaries \
    --start-time "$START_TIME" \
    --end-time "$END_TIME" \
    --region "$REGION" \
    --query 'length(TraceSummaries)' \
    --output text 2>/dev/null | awk 'NR==1 {print $1}'); then
    if [[ "${TRACE_COUNT:-0}" =~ ^[0-9]+$ ]] && [[ "${TRACE_COUNT}" -gt 0 ]]; then
      log_success "X-Ray: $TRACE_COUNT trace(s) in last hour"
      add_json_result "xray" "ok" "$TRACE_COUNT traces found"
    else
      log_info "X-Ray: No recent traces (service may not be active)"
      add_json_result "xray" "ok" "No recent traces"
    fi
  else
    log_warning "X-Ray: Unable to query traces"
    add_json_result "xray" "warning" "Unable to query"
  fi
}

check_costs() {
  log_info "Checking estimated costs (current month)"

  START_DATE=$(date -u '+%Y-%m-01')
  END_DATE=$(date -u '+%Y-%m-%d')

  if COST=$(aws ce get-cost-and-usage \
    --time-period Start="$START_DATE",End="$END_DATE" \
    --granularity MONTHLY \
    --metrics BlendedCost \
    --region us-east-1 \
    --query 'ResultsByTime[0].Total.BlendedCost.Amount' \
    --output text 2>/dev/null); then
    COST_ROUNDED=$(printf "%.2f" "$COST")
    log_info "Current month cost: \$$COST_ROUNDED USD"
    add_json_result "costs" "ok" "\$$COST_ROUNDED USD"
  else
    log_warning "Unable to fetch cost data"
    add_json_result "costs" "warning" "Unable to fetch"
  fi
}

print_summary() {
  if [[ "$JSON_OUTPUT" == "true" ]]; then
    echo "$JSON_RESULTS" | jq .
  else
    echo ""
    echo "================================================"
    echo "  Health Check Summary"
    echo "================================================"
    echo ""
    echo "Region: $REGION"
    echo "Account: $ACCOUNT_ID"
    echo ""

    # Count statuses
    local ok_count=$(echo "$JSON_RESULTS" | jq '[.[] | select(.status == "ok")] | length')
    local warning_count=$(echo "$JSON_RESULTS" | jq '[.[] | select(.status == "warning" or .status == "partial" or .status == "in_progress")] | length')
    local error_count=$(echo "$JSON_RESULTS" | jq '[.[] | select(.status == "error")] | length')
    local not_found_count=$(echo "$JSON_RESULTS" | jq '[.[] | select(.status == "not_found" or .status == "not_configured")] | length')

    echo -e "${GREEN}✓${NC} Healthy: $ok_count"
    echo -e "${YELLOW}⚠${NC} Warnings: $warning_count"
    echo -e "${RED}✗${NC} Errors: $error_count"
    echo "ℹ Not configured: $not_found_count"
    echo ""

    if [[ $warning_count -gt 0 ]]; then
      echo -e "${YELLOW}Note:${NC} Some resources may be incurring costs. Review warnings above."
    fi
  fi
}

main() {
  if [[ "$JSON_OUTPUT" == "false" ]]; then
    echo "================================================"
    echo "  AgentEval AWS Services Health Check"
    echo "================================================"
    echo ""
  fi

  check_aws_cli
  check_cloudformation
  check_dynamodb
  check_s3
  check_eventbridge
  check_ecs
  check_ec2
  check_bedrock
  check_xray
  check_costs

  print_summary
}

main
