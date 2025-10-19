#!/usr/bin/env bash
# Master Orchestration Script for AgentEval Live Demo
# Runs complete end-to-end demo: setup → execute → pull results

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
REGION="${AWS_REGION:-us-east-1}"
SETUP_INFRA="${SETUP_INFRA:-true}"
PULL_RESULTS="${PULL_RESULTS:-true}"
AUTO_TEARDOWN="${AUTO_TEARDOWN:-false}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --region)
            REGION="$2"
            shift 2
            ;;
        --skip-setup)
            SETUP_INFRA="false"
            shift
            ;;
        --skip-pull)
            PULL_RESULTS="false"
            shift
            ;;
        --auto-teardown)
            AUTO_TEARDOWN="true"
            shift
            ;;
        --quick)
            QUICK_MODE="--quick"
            shift
            ;;
        --help)
            cat << 'EOF'
AgentEval Full Demo Orchestration Script

Usage: scripts/run-full-demo.sh [OPTIONS]

Options:
  --region REGION        AWS region (default: us-east-1)
  --skip-setup           Skip AWS infrastructure setup
  --skip-pull            Skip results pulling after demo
  --auto-teardown        Clean up AWS resources after demo
  --quick                Run demo in quick mode (no turn execution)
  --help                 Show this help message

Examples:
  # Full end-to-end demo with setup and results
  scripts/run-full-demo.sh

  # Quick demo without infrastructure setup
  scripts/run-full-demo.sh --skip-setup --quick

  # Full demo with automatic cleanup
  scripts/run-full-demo.sh --auto-teardown

EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

QUICK_MODE="${QUICK_MODE:-}"

# Banner
cat << 'EOF'
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║    █████╗  ██████╗ ███████╗███╗   ██╗████████╗███████╗██╗   ██╗    ║
║   ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝██╔════╝██║   ██║    ║
║   ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   █████╗  ██║   ██║    ║
║   ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   ██╔══╝  ╚██╗ ██╔╝    ║
║   ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   ███████╗ ╚████╔╝     ║
║   ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚══════╝  ╚═══╝      ║
║                                                                      ║
║            Full End-to-End Demo with Results Extraction            ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
EOF

echo ""
echo "Configuration:"
echo "  Region: ${REGION}"
echo "  Setup Infrastructure: ${SETUP_INFRA}"
echo "  Pull Results: ${PULL_RESULTS}"
echo "  Auto Teardown: ${AUTO_TEARDOWN}"
echo "  Quick Mode: ${QUICK_MODE:-false}"
echo ""

# Track success
DEMO_SUCCESS=false

# Step 1: Setup AWS Infrastructure
if [ "$SETUP_INFRA" = "true" ]; then
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  STEP 1: Setting Up AWS Infrastructure                  ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if bash "${SCRIPT_DIR}/setup-live-demo.sh" --region "${REGION}"; then
        echo -e "${GREEN}✓ Infrastructure setup complete${NC}"
    else
        echo -e "${RED}✗ Infrastructure setup failed${NC}"
        exit 1
    fi
    echo ""
    sleep 2
else
    echo -e "${YELLOW}⊙ Skipping infrastructure setup${NC}"
    echo ""
fi

# Step 2: Run AgentEval Demo
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  STEP 2: Running AgentEval Live Demo                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

DEMO_CMD="python demo/agenteval_chatbot_demo.py --region ${REGION}"
if [ -n "$QUICK_MODE" ]; then
    DEMO_CMD="$DEMO_CMD $QUICK_MODE"
fi

echo "Executing: $DEMO_CMD"
echo ""

if eval "$DEMO_CMD"; then
    echo -e "${GREEN}✓ Demo execution complete${NC}"
    DEMO_SUCCESS=true
else
    echo -e "${RED}✗ Demo execution failed${NC}"
    DEMO_SUCCESS=false
fi
echo ""
sleep 2

# Step 3: Pull Results
if [ "$PULL_RESULTS" = "true" ]; then
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  STEP 3: Pulling Results from AWS                       ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if bash "${SCRIPT_DIR}/pull-demo-results.sh"; then
        echo -e "${GREEN}✓ Results pulled successfully${NC}"
    else
        echo -e "${YELLOW}⚠ Results pulling encountered issues (non-fatal)${NC}"
    fi
    echo ""
    sleep 2
else
    echo -e "${YELLOW}⊙ Skipping results pulling${NC}"
    echo ""
fi

# Step 4: Generate Quick Analysis
if [ "$PULL_RESULTS" = "true" ] && [ "$DEMO_SUCCESS" = "true" ]; then
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  STEP 4: Generating Quick Analysis                      ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    CAMPAIGN_FILE="${REPO_ROOT}/demo/evidence/campaign-data/campaigns.json"
    TURNS_FILE="${REPO_ROOT}/demo/evidence/campaign-data/turns.json"

    if [ -f "$CAMPAIGN_FILE" ]; then
        echo -e "${BLUE}━━━ Campaign Summary ━━━${NC}"
        jq -r '.Items[] | "\nCampaign: \(.campaign_id.S)\n  Type: \(.campaign_type.S)\n  Status: \(.status.S)\n  Completed Turns: \(.stats.M.completed_turns.N)/\(.stats.M.total_turns.N)\n  Average Score: \(.stats.M.avg_score.N)\n  Failed Turns: \(.stats.M.failed_turns.N)"' "$CAMPAIGN_FILE"
    fi

    if [ -f "$TURNS_FILE" ]; then
        echo -e "\n${BLUE}━━━ Turn Examples ━━━${NC}"
        jq -r '.Items[0:2][] | "\nTurn \(.turn_number.N):\n  User: \(.user_message.S)\n  Bot: \(.system_response.S)"' "$TURNS_FILE"
    fi

    echo ""
    echo -e "${BLUE}━━━ Evidence Location ━━━${NC}"
    echo "  All results: ${REPO_ROOT}/demo/evidence/"
    echo "  Reports: ${REPO_ROOT}/demo/evidence/pulled-reports/"
    echo "  Raw data: ${REPO_ROOT}/demo/evidence/campaign-data/"
    echo "  Summary: ${REPO_ROOT}/demo/evidence/SUMMARY.md"
    echo ""
fi

# Step 5: Teardown (if requested)
if [ "$AUTO_TEARDOWN" = "true" ]; then
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  STEP 5: Cleaning Up AWS Resources                      ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if bash "${SCRIPT_DIR}/teardown-live-demo.sh" --region "${REGION}"; then
        echo -e "${GREEN}✓ Cleanup complete${NC}"
    else
        echo -e "${YELLOW}⚠ Cleanup encountered issues${NC}"
    fi
    echo ""
fi

# Final Summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
if [ "$DEMO_SUCCESS" = "true" ]; then
    echo -e "${GREEN}║           ✓ FULL DEMO COMPLETED SUCCESSFULLY             ║${NC}"
else
    echo -e "${YELLOW}║           ⚠ DEMO COMPLETED WITH ISSUES                   ║${NC}"
fi
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ "$PULL_RESULTS" = "true" ]; then
    echo "📊 Review your results:"
    echo "   cat demo/evidence/SUMMARY.md"
    echo "   jq . demo/evidence/campaign-data/campaigns.json"
    echo ""
fi

echo "🎯 Next steps:"
echo "   • Review reports in demo/evidence/"
echo "   • Analyze metrics to improve your chatbot"
echo "   • Run more campaigns with different personas"
echo "   • Deploy to production!"
echo ""

exit 0
