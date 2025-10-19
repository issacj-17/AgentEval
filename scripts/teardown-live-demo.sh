#!/usr/bin/env bash

# AgentEval Live Demo Teardown Script
# ====================================
# Cleans up all AWS resources created by setup-live-demo.sh
# IMPORTANT: This will DELETE all data and resources!

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

REGION="${AWS_REGION:-us-east-1}"
STACK_NAME="${AGENTEVAL_STACK_NAME:-agenteval-live-demo}"
FORCE=false

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
Usage: scripts/teardown-live-demo.sh [options]

Options:
  --region <aws-region>    AWS region (default: us-east-1 or $AWS_REGION)
  --force                  Skip confirmation prompts
  --keep-tables           Keep DynamoDB tables (only delete data)
  --keep-buckets          Keep S3 buckets (only delete objects)
  -h, --help              Show this help message

Example:
  scripts/teardown-live-demo.sh --region us-east-1 --force

WARNING: This will delete all AgentEval live demo resources!
USAGE
}

KEEP_TABLES=false
KEEP_BUCKETS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --region)
      REGION="$2"; shift 2 ;;
    --force)
      FORCE=true; shift 1 ;;
    --keep-tables)
      KEEP_TABLES=true; shift 1 ;;
    --keep-buckets)
      KEEP_BUCKETS=true; shift 1 ;;
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
echo "  AgentEval Live Demo Teardown"
echo "================================================"
echo ""

# Check AWS CLI
if ! command -v aws >/dev/null 2>&1; then
  log_error "AWS CLI not installed"
  exit 1
fi

if ! aws sts get-caller-identity --region "$REGION" >/dev/null 2>&1; then
  log_error "AWS CLI not configured or credentials invalid"
  exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)

# Confirmation prompt
if [ "$FORCE" = "false" ]; then
  echo ""
  log_warning "This will DELETE the following resources:"
  echo "  - DynamoDB tables and all data"
  echo "  - S3 buckets and all objects"
  echo "  - EventBridge event bus"
  echo ""
  echo "Region: $REGION"
  echo "Account: $ACCOUNT_ID"
  echo ""
  if ! read -r -t 10 -p "Are you sure you want to continue? (type 'yes' to confirm within 10s): " confirm; then
    log_warning "No response received within 10 seconds. Proceeding with teardown."
    confirm="yes"
  fi
  if [ "$confirm" != "yes" ]; then
    log_info "Teardown cancelled"
    exit 0
  fi
fi

echo ""
log_info "Starting teardown in region: $REGION"

# Delete S3 bucket contents and buckets
log_info "Cleaning up S3 buckets..."

RESULTS_BUCKET="agenteval-results-${ACCOUNT_ID}"
REPORTS_BUCKET="agenteval-reports-${ACCOUNT_ID}"

delete_bucket_contents() {
  local bucket=$1

  if aws s3 ls "s3://$bucket" --region "$REGION" 2>/dev/null; then
    log_info "Deleting objects from bucket: $bucket"

    # Delete all objects and versions
    aws s3 rm "s3://$bucket" --recursive --region "$REGION" 2>/dev/null || true

    # Delete all versions if versioning is enabled
    aws s3api list-object-versions \
      --bucket "$bucket" \
      --region "$REGION" \
      --output json 2>/dev/null | \
    jq -r '.Versions[]?, .DeleteMarkers[]? | "\(.Key) \(.VersionId)"' 2>/dev/null | \
    while read -r key version_id; do
      if [ -n "$key" ] && [ -n "$version_id" ]; then
        aws s3api delete-object \
          --bucket "$bucket" \
          --key "$key" \
          --version-id "$version_id" \
          --region "$REGION" >/dev/null 2>&1 || true
      fi
    done

    if [ "$KEEP_BUCKETS" = "false" ]; then
      log_info "Deleting bucket: $bucket"
      aws s3 rb "s3://$bucket" --force --region "$REGION" 2>/dev/null || true
      log_success "Bucket $bucket deleted"
    else
      log_info "Bucket $bucket emptied (kept as requested)"
    fi
  else
    log_info "Bucket $bucket does not exist (already deleted)"
  fi
}

delete_bucket_contents "$RESULTS_BUCKET"
delete_bucket_contents "$REPORTS_BUCKET"

# Delete DynamoDB table data and tables
log_info "Cleaning up DynamoDB tables..."

TABLES=(
  "agenteval-campaigns"
  "agenteval-turns"
  "agenteval-evaluations"
  "agenteval-attack-knowledge"
)

delete_table_data() {
  local table=$1

  if aws dynamodb describe-table --table-name "$table" --region "$REGION" >/dev/null 2>&1; then
    if [ "$KEEP_TABLES" = "false" ]; then
      log_info "Deleting table: $table"
      aws dynamodb delete-table --table-name "$table" --region "$REGION" >/dev/null 2>&1 || true

      # Wait for deletion
      log_info "Waiting for table $table to be deleted..."
      aws dynamodb wait table-not-exists --table-name "$table" --region "$REGION" 2>/dev/null || true
      log_success "Table $table deleted"
    else
      log_info "Deleting data from table: $table"
      # Scan and delete all items
      aws dynamodb scan \
        --table-name "$table" \
        --region "$REGION" \
        --output json 2>/dev/null | \
      jq -r '.Items[] | "\(.PK.S) \(.SK.S)"' 2>/dev/null | \
      while read -r pk sk; do
        if [ -n "$pk" ] && [ -n "$sk" ]; then
          aws dynamodb delete-item \
            --table-name "$table" \
            --key "{\"PK\":{\"S\":\"$pk\"},\"SK\":{\"S\":\"$sk\"}}" \
            --region "$REGION" >/dev/null 2>&1 || true
        fi
      done
      log_success "Data deleted from table $table (table kept)"
    fi
  else
    log_info "Table $table does not exist (already deleted)"
  fi
}

for table in "${TABLES[@]}"; do
  delete_table_data "$table"
done

# Delete EventBridge event bus
log_info "Cleaning up EventBridge event bus..."

BUS_NAME="agenteval"

if aws events describe-event-bus --name "$BUS_NAME" --region "$REGION" >/dev/null 2>&1; then
  log_info "Deleting event bus: $BUS_NAME"

  # Delete all rules on the bus first
  RULES=$(aws events list-rules --event-bus-name "$BUS_NAME" --region "$REGION" --query 'Rules[].Name' --output text 2>/dev/null || echo "")
  if [ -n "$RULES" ]; then
    for rule in $RULES; do
      log_info "Removing targets from rule: $rule"
      TARGETS=$(aws events list-targets-by-rule --event-bus-name "$BUS_NAME" --rule "$rule" --region "$REGION" --query 'Targets[].Id' --output text 2>/dev/null || echo "")
      if [ -n "$TARGETS" ]; then
        aws events remove-targets --event-bus-name "$BUS_NAME" --rule "$rule" --ids $TARGETS --region "$REGION" >/dev/null 2>&1 || true
      fi

      log_info "Deleting rule: $rule"
      aws events delete-rule --event-bus-name "$BUS_NAME" --name "$rule" --region "$REGION" >/dev/null 2>&1 || true
    done
  fi

  aws events delete-event-bus --name "$BUS_NAME" --region "$REGION" >/dev/null 2>&1 || true
  log_success "Event bus $BUS_NAME deleted"
else
  log_info "Event bus $BUS_NAME does not exist (already deleted)"
fi

# Remove configuration file
if [ -f ".env.live-demo" ]; then
  log_warning ".env.live-demo preserved (remove manually if desired)."
fi

echo ""
echo "================================================"
echo "  Teardown Complete!"
echo "================================================"
echo ""
echo "All AgentEval live demo resources have been cleaned up."
echo ""
echo "To verify cleanup:"
echo "  scripts/check-aws-services.sh --region $REGION"
echo ""
echo "Resources cleaned:"
if [ "$KEEP_BUCKETS" = "false" ]; then
  echo "  ✓ S3 buckets deleted"
else
  echo "  ✓ S3 buckets emptied (kept)"
fi

if [ "$KEEP_TABLES" = "false" ]; then
  echo "  ✓ DynamoDB tables deleted"
else
  echo "  ✓ DynamoDB tables emptied (kept)"
fi

echo "  ✓ EventBridge event bus deleted"
if [ -f ".env.live-demo" ]; then
  echo "  ⚠ .env.live-demo preserved"
else
  echo "  ✓ Configuration file removed"
fi
echo ""
