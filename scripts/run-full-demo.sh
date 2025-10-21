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

# Step 3: Pull Results (REMOVED - demo script handles this internally)
# The agenteval_chatbot_demo.py script already pulls results to the correct location
# via demo/agenteval_live_demo.py's pull_results() method, so this step is redundant
if [ "$PULL_RESULTS" = "true" ]; then
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  STEP 3: Results Already Pulled by Demo Script          ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}✓ Results automatically pulled to outputs/{timestamp}-run/ by demo script${NC}"
    echo ""
    sleep 2
else
    echo -e "${YELLOW}⊙ Skipping results pulling${NC}"
    echo ""
fi

# Step 4: Display Results Location
if [ "$DEMO_SUCCESS" = "true" ]; then
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  STEP 4: Results Summary                                 ║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Find latest output directory
    LATEST_OUTPUT="${REPO_ROOT}/outputs/latest"

    if [ -L "$LATEST_OUTPUT" ]; then
        echo -e "${GREEN}✓ Results generated successfully${NC}"
        echo ""
        echo -e "${BLUE}━━━ Output Location ━━━${NC}"
        echo "  All results: ${LATEST_OUTPUT}/"
        echo "  HTML Dashboard: ${LATEST_OUTPUT}/reports/dashboard.html"
        echo "  Campaign Details: ${LATEST_OUTPUT}/reports/campaign_*.html"
        echo "  Markdown Reports: ${LATEST_OUTPUT}/dashboard.md"
        echo "  Summary: ${LATEST_OUTPUT}/summary.md"
        echo "  Logs: ${LATEST_OUTPUT}/logs/"
        echo ""
        echo -e "${BLUE}━━━ Quick Stats ━━━${NC}"

        # Count campaigns
        CAMPAIGN_COUNT=$(find "${LATEST_OUTPUT}/campaigns" -maxdepth 1 -type d | tail -n +2 | wc -l | tr -d ' ')
        echo "  Campaigns evaluated: ${CAMPAIGN_COUNT}"

        # Count HTML reports
        HTML_COUNT=$(find "${LATEST_OUTPUT}/reports" -name "campaign_*.html" 2>/dev/null | wc -l | tr -d ' ')
        echo "  Detail pages generated: ${HTML_COUNT}"
    else
        echo -e "${YELLOW}⚠ Latest output symlink not found${NC}"
        echo "  Results may be in: ${REPO_ROOT}/outputs/"
    fi
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

echo "📊 Review your results:"
echo "   # Open interactive HTML dashboard"
echo "   open outputs/latest/reports/dashboard.html"
echo ""
echo "   # View markdown reports"
echo "   cat outputs/latest/dashboard.md"
echo "   cat outputs/latest/summary.md"
echo ""
echo "   # Explore campaign details"
echo "   ls outputs/latest/reports/campaign_*.html"
echo ""

echo "🎯 Next steps:"
echo "   • Click 'View Details' on any campaign to see chatbot responses"
echo "   • Analyze metrics to improve your chatbot"
echo "   • Run more campaigns with different personas"
echo "   • Deploy to production!"
echo ""

exit 0
