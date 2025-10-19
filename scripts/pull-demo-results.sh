#!/usr/bin/env bash
# Pull Demo Results Script
# Downloads all reports, logs, and results from AWS to local directory

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

# Configuration
REGION="${AWS_REGION:-us-east-1}"
RESULTS_BUCKET="${AWS_S3_RESULTS_BUCKET:-agenteval-results-585049192332}"
REPORTS_BUCKET="${AWS_S3_REPORTS_BUCKET:-agenteval-reports-585049192332}"
EVIDENCE_DIR="${REPO_ROOT}/demo/evidence"
PULLED_REPORTS_DIR="${EVIDENCE_DIR}/pulled-reports"
TRACE_REPORTS_DIR="${EVIDENCE_DIR}/trace-reports"
CAMPAIGN_DATA_DIR="${EVIDENCE_DIR}/campaign-data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  AgentEval Demo Results Puller${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""
echo "Region: ${REGION}"
echo "Results Bucket: ${RESULTS_BUCKET}"
echo "Reports Bucket: ${REPORTS_BUCKET}"
echo "Evidence Directory: ${EVIDENCE_DIR}"
echo ""

# Create evidence directories if they don't exist
mkdir -p "${PULLED_REPORTS_DIR}"
mkdir -p "${TRACE_REPORTS_DIR}"
mkdir -p "${CAMPAIGN_DATA_DIR}"

# Function to pull campaign data from DynamoDB
pull_campaign_data() {
    echo -e "${BLUE}ℹ${NC} Pulling campaign data from DynamoDB..."

    local campaigns_file="${CAMPAIGN_DATA_DIR}/campaigns.json"
    local turns_file="${CAMPAIGN_DATA_DIR}/turns.json"
    local evaluations_file="${CAMPAIGN_DATA_DIR}/evaluations.json"

    # Pull campaigns
    if aws dynamodb scan \
        --table-name agenteval-campaigns \
        --region "${REGION}" \
        --output json > "${campaigns_file}" 2>/dev/null; then
        local campaign_count=$(jq '.Items | length' "${campaigns_file}")
        echo -e "${GREEN}✓${NC} Pulled ${campaign_count} campaigns to ${campaigns_file}"
    else
        echo -e "${YELLOW}⚠${NC} Could not pull campaigns (table may not exist yet)"
    fi

    # Pull turns
    if aws dynamodb scan \
        --table-name agenteval-turns \
        --region "${REGION}" \
        --output json > "${turns_file}" 2>/dev/null; then
        local turn_count=$(jq '.Items | length' "${turns_file}")
        echo -e "${GREEN}✓${NC} Pulled ${turn_count} turns to ${turns_file}"
    else
        echo -e "${YELLOW}⚠${NC} Could not pull turns (table may not exist yet)"
    fi

    # Pull evaluations
    if aws dynamodb scan \
        --table-name agenteval-evaluations \
        --region "${REGION}" \
        --output json > "${evaluations_file}" 2>/dev/null; then
        local eval_count=$(jq '.Items | length' "${evaluations_file}")
        echo -e "${GREEN}✓${NC} Pulled ${eval_count} evaluations to ${evaluations_file}"
    else
        echo -e "${YELLOW}⚠${NC} Could not pull evaluations (table may not exist yet)"
    fi
}

# Function to pull S3 reports
pull_s3_reports() {
    echo -e "${BLUE}ℹ${NC} Pulling reports from S3..."

    # Pull campaign reports from results bucket
    local campaign_reports_dir="${PULLED_REPORTS_DIR}/campaign-reports"
    mkdir -p "${campaign_reports_dir}"

    if aws s3 ls "s3://${RESULTS_BUCKET}/campaigns/" --region "${REGION}" > /dev/null 2>&1; then
        aws s3 sync \
            "s3://${RESULTS_BUCKET}/campaigns/" \
            "${campaign_reports_dir}/" \
            --region "${REGION}" \
            --exclude "*" \
            --include "*/report-*.json" \
            --include "*/results.json" 2>&1 | grep -v "download:" || true

        local report_count=$(find "${campaign_reports_dir}" -name "*.json" | wc -l | tr -d ' ')
        echo -e "${GREEN}✓${NC} Pulled ${report_count} campaign reports to ${campaign_reports_dir}"
    else
        echo -e "${YELLOW}⚠${NC} Results bucket not accessible or empty"
    fi

    # Pull demo reports from reports bucket
    local demo_reports_dir="${PULLED_REPORTS_DIR}/demo-reports"
    mkdir -p "${demo_reports_dir}"

    if aws s3 ls "s3://${REPORTS_BUCKET}/reports/" --region "${REGION}" > /dev/null 2>&1; then
        aws s3 sync \
            "s3://${REPORTS_BUCKET}/reports/" \
            "${demo_reports_dir}/" \
            --region "${REGION}" 2>&1 | grep -v "download:" || true

        local demo_report_count=$(find "${demo_reports_dir}" -name "*.json" | wc -l | tr -d ' ')
        echo -e "${GREEN}✓${NC} Pulled ${demo_report_count} demo reports to ${demo_reports_dir}"
    else
        echo -e "${YELLOW}⚠${NC} Reports bucket not accessible or empty"
    fi
}

# Function to pull X-Ray traces
pull_xray_traces() {
    echo -e "${BLUE}ℹ${NC} Pulling X-Ray traces..."

    # Get traces from the last 2 hours
    local start_time=$(date -u -v-2H '+%s' 2>/dev/null || date -u -d '2 hours ago' '+%s')
    local end_time=$(date -u '+%s')

    local traces_file="${TRACE_REPORTS_DIR}/traces-$(date -u '+%Y%m%d-%H%M%S').json"

    if aws xray get-trace-summaries \
        --start-time "${start_time}" \
        --end-time "${end_time}" \
        --region "${REGION}" \
        --output json > "${traces_file}" 2>/dev/null; then
        local trace_count=$(jq '.TraceSummaries | length' "${traces_file}")
        echo -e "${GREEN}✓${NC} Pulled ${trace_count} trace summaries to ${traces_file}"
    else
        echo -e "${YELLOW}⚠${NC} Could not pull X-Ray traces (may not be enabled)"
    fi
}

# Function to generate summary report
generate_summary() {
    echo -e "${BLUE}ℹ${NC} Generating evidence summary..."

    local summary_file="${EVIDENCE_DIR}/SUMMARY.md"

    cat > "${summary_file}" << 'EOF'
# AgentEval Demo Evidence Summary

This directory contains all pulled reports, logs, and data from the live demo execution.

## Directory Structure

```
demo/evidence/
├── pulled-reports/
│   ├── campaign-reports/    # Detailed campaign reports from S3
│   └── demo-reports/         # Demo summary reports from S3
├── campaign-data/
│   ├── campaigns.json        # All campaigns from DynamoDB
│   ├── turns.json            # All turns from DynamoDB
│   └── evaluations.json      # All evaluations from DynamoDB
├── trace-reports/
│   └── traces-*.json         # X-Ray trace summaries
└── SUMMARY.md                # This file

## How to Review Results

### 1. Quick Summary
```bash
# View campaign summary
jq '.Items[] | {
  campaign_id: .campaign_id.S,
  type: .campaign_type.S,
  status: .status.S,
  completed_turns: .stats.M.completed_turns.N,
  avg_score: .stats.M.avg_score.N
}' demo/evidence/campaign-data/campaigns.json
```

### 2. Detailed Campaign Report
```bash
# Find the latest campaign report
LATEST_REPORT=$(find demo/evidence/pulled-reports/campaign-reports -name "report-*.json" | sort | tail -1)

# View with pretty formatting
jq . "$LATEST_REPORT" | less

# Extract key metrics
jq '.aggregate_metrics' "$LATEST_REPORT"
```

### 3. Turn-by-Turn Analysis
```bash
# View each turn with user/system messages and scores
jq -r '.turn_results[] | "
Turn \(.turn_number):
  User: \(.user_message)
  System: \(.system_response)
  Overall Score: \(.evaluation.aggregate_scores.overall // "N/A")
  Metrics:
\(.evaluation.metric_results | to_entries[] | "    - \(.key): \(.value.score)")
"' "$LATEST_REPORT"
```

### 4. Persona Memory State
```bash
# View how persona state evolved
jq '.Items[] | select(.persona_memory) | {
  turn: .turn_id.S,
  frustration: .persona_memory.M.state.M.frustration_level.N,
  goal_progress: .persona_memory.M.state.M.goal_progress.N,
  satisfaction: .persona_memory.M.state.M.satisfaction_score.N
}' demo/evidence/campaign-data/turns.json
```

### 5. Check for Response Echoing
```bash
# Verify system responses are not echoing user messages
jq -r '.Items[] | "User: \(.user_message.S)\nBot: \(.system_response.S)\n---"' \
  demo/evidence/campaign-data/turns.json | head -50
```

## Key Validation Checks

### ✅ System Responses Working Correctly
- System responses should contain only chatbot replies
- No echoed user messages
- No raw JSON structures
- No serialized objects

### ✅ OpenTelemetry Traces
- Trace IDs present in turn data
- Spans exported to console/collector
- No initialization failures

### ✅ Comprehensive Evaluations
- 11 metrics evaluated per turn
- Detailed reasoning provided
- Pass/fail indicators
- Confidence scores

## Generated On
EOF

    date -u '+%Y-%m-%d %H:%M:%S UTC' >> "${summary_file}"

    echo -e "${GREEN}✓${NC} Generated summary at ${summary_file}"
}

# Main execution
main() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Step 1: Pulling Campaign Data from DynamoDB${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    pull_campaign_data
    echo ""

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Step 2: Pulling Reports from S3${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    pull_s3_reports
    echo ""

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Step 3: Pulling X-Ray Traces${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    pull_xray_traces
    echo ""

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Step 4: Generating Summary${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    generate_summary
    echo ""

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✓ Results Pull Complete!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "All results saved to: ${EVIDENCE_DIR}"
    echo ""
    echo "Next steps:"
    echo "  1. Review summary: cat ${EVIDENCE_DIR}/SUMMARY.md"
    echo "  2. View reports: ls -la ${PULLED_REPORTS_DIR}/"
    echo "  3. Analyze data: jq . ${CAMPAIGN_DATA_DIR}/campaigns.json"
    echo ""
}

main
