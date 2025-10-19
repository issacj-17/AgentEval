#!/usr/bin/env bash

# AgentEval Live Demo Setup Verification Script
# ==============================================
# Verifies that all components for live demo are in place
# Run this before attempting the live demo

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

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

ERRORS=0
WARNINGS=0

check_requirement() {
  local name=$1
  local command=$2
  local help_text=$3

  if eval "$command" >/dev/null 2>&1; then
    log_success "$name is available"
  else
    log_error "$name is NOT available"
    if [ -n "$help_text" ]; then
      echo "  → $help_text"
    fi
    ((ERRORS++))
  fi
}

check_file() {
  local name=$1
  local path=$2
  local required=$3

  if [ -f "$path" ]; then
    log_success "$name exists: $path"
  else
    if [ "$required" = "required" ]; then
      log_error "$name is MISSING: $path"
      ((ERRORS++))
    else
      log_warning "$name is missing: $path (optional)"
      ((WARNINGS++))
    fi
  fi
}

echo ""
echo "================================================"
echo "  AgentEval Live Demo Verification"
echo "================================================"
echo ""

# Check Python
log_info "Checking Python environment..."
check_requirement "Python 3" "command -v python3" "Install Python 3.8 or higher"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
  log_info "  Python version: $PYTHON_VERSION"
fi

# Check pip
check_requirement "pip" "command -v pip" "Install pip: python3 -m ensurepip"

# Check virtual environment
if [ -n "${VIRTUAL_ENV:-}" ]; then
  log_success "Virtual environment is active: $VIRTUAL_ENV"
else
  log_warning "Not in a virtual environment"
  log_info "  → Recommended: python3 -m venv .venv && source .venv/bin/activate"
  ((WARNINGS++))
fi

# Check AWS CLI
log_info ""
log_info "Checking AWS CLI..."
check_requirement "AWS CLI" "command -v aws" "Install: https://aws.amazon.com/cli/"

if command -v aws >/dev/null 2>&1; then
  AWS_VERSION=$(aws --version 2>&1 | awk '{print $1}')
  log_info "  AWS CLI version: $AWS_VERSION"

  # Check AWS credentials
  if aws sts get-caller-identity >/dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
    log_success "AWS credentials are configured (Account: $ACCOUNT_ID)"
  else
    log_error "AWS credentials are NOT configured"
    log_info "  → Run: aws configure"
    ((ERRORS++))
  fi
fi

# Check jq (optional but helpful)
log_info ""
log_info "Checking optional tools..."
if command -v jq >/dev/null 2>&1; then
  log_success "jq is available (helpful for JSON parsing)"
else
  log_warning "jq is not available (optional)"
  log_info "  → Install: brew install jq (macOS) or apt-get install jq (Linux)"
  ((WARNINGS++))
fi

# Check scripts
log_info ""
log_info "Checking demo scripts..."
check_file "Setup script" "scripts/setup-live-demo.sh" "required"
check_file "Teardown script" "scripts/teardown-live-demo.sh" "required"
check_file "Run script" "scripts/run-live-demo.sh" "required"
check_file "Check services script" "scripts/check-aws-services.sh" "required"

# Check script permissions
if [ -f "scripts/setup-live-demo.sh" ]; then
  if [ -x "scripts/setup-live-demo.sh" ]; then
    log_success "Setup script is executable"
  else
    log_warning "Setup script is not executable"
    log_info "  → Run: chmod +x scripts/*.sh"
    ((WARNINGS++))
  fi
fi

# Check demo files
log_info ""
log_info "Checking demo applications..."
check_file "Mock demo" "demo/agenteval_demo_mock.py" "required"
check_file "Live demo" "demo/agenteval_live_demo.py" "required"
check_file "Demo README" "demo/README.md" "optional"

# Check documentation
log_info ""
log_info "Checking documentation..."
check_file "Live demo guide" "LIVE_DEMO_GUIDE.md" "optional"
check_file "Main README" "README.md" "required"

# Check Python package
log_info ""
log_info "Checking Python package installation..."
if python3 -c "import agenteval" 2>/dev/null; then
  log_success "AgentEval package is installed"
else
  log_error "AgentEval package is NOT installed"
  log_info "  → Run: pip install -e \".[dev]\""
  ((ERRORS++))
fi

# Check key Python dependencies
log_info ""
log_info "Checking key dependencies..."
check_requirement "aioboto3" "python3 -c 'import aioboto3'" "Install: pip install aioboto3"
check_requirement "boto3" "python3 -c 'import boto3'" "Install: pip install boto3"
check_requirement "fastapi" "python3 -c 'import fastapi'" "Install: pip install fastapi"
check_requirement "pydantic" "python3 -c 'import pydantic'" "Install: pip install pydantic"
check_requirement "python-dotenv" "python3 -c 'import dotenv'" "Install: pip install python-dotenv"

# Check for .env.live-demo (not created yet)
log_info ""
log_info "Checking configuration..."
if [ -f ".env.live-demo" ]; then
  log_success "Live demo configuration exists: .env.live-demo"
  log_info "  → This means setup has already been run"
else
  log_info "Live demo configuration not found (expected before first run)"
  log_info "  → Will be created by: scripts/setup-live-demo.sh"
fi

# Summary
echo ""
echo "================================================"
echo "  Verification Summary"
echo "================================================"
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
  log_success "All checks passed! You're ready to run the live demo."
  echo ""
  echo "Next steps:"
  echo "  1. Run setup: scripts/setup-live-demo.sh --region us-east-1"
  echo "  2. Run demo: python demo/agenteval_live_demo.py"
  echo "  3. Cleanup: scripts/teardown-live-demo.sh"
  echo ""
  exit 0
elif [ $ERRORS -eq 0 ]; then
  log_warning "$WARNINGS warning(s) found (non-critical)"
  echo ""
  echo "You can proceed with the live demo, but consider addressing warnings."
  echo ""
  echo "Next steps:"
  echo "  1. Run setup: scripts/setup-live-demo.sh --region us-east-1"
  echo "  2. Run demo: python demo/agenteval_live_demo.py"
  echo ""
  exit 0
else
  log_error "$ERRORS error(s) and $WARNINGS warning(s) found"
  echo ""
  echo "Please fix the errors above before running the live demo."
  echo ""
  echo "Common fixes:"
  echo "  • Install dependencies: pip install -e \".[dev]\""
  echo "  • Configure AWS: aws configure"
  echo "  • Make scripts executable: chmod +x scripts/*.sh"
  echo ""
  exit 1
fi
