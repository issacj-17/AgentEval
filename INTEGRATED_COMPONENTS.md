# AgentEval Integrated Components

**Last Updated**: October 19, 2025 **Integration Status**: ✅ Complete

## Overview

All reporting and evaluation components are now fully integrated into the Campaign Orchestrator for
seamless, automated evaluation workflows. When a campaign completes, all necessary reports and
dashboards are automatically generated without manual intervention.

______________________________________________________________________

## Automatic Integration Pipeline

### Phase 1: Campaign Execution

**Component**: `CampaignOrchestrator` (src/agenteval/orchestration/campaign.py)

The orchestrator manages the entire campaign lifecycle:

1. Campaign creation and initialization
1. Turn execution (persona/red team interactions)
1. Real-time evaluation with judge agents
1. Metrics aggregation and scoring
1. Report generation

**Status**: ✅ Core functionality

______________________________________________________________________

### Phase 2: Auto-Pull Results (Lines 460-501)

**Component**: `pull_campaign_data` (src/agenteval/reporting/pull.py)

**Trigger**: Automatic after campaign completion **Configuration**: `auto_pull_results_to_local`
(default: `True`)

**What It Does**:

- Downloads campaign data from DynamoDB (campaigns, turns, evaluations)
- Downloads reports from S3 (aggregate metrics, analysis)
- Saves to local directory: `outputs/campaign-results/<campaign_id>/`

**Output Structure**:

```
outputs/campaign-results/
└── <campaign_id>/
    ├── dynamodb/
    │   ├── campaign.json          # Campaign metadata
    │   ├── turns.json              # Turn-by-turn data
    │   └── evaluations.json        # Evaluation results
    └── s3/
        └── results/
            └── report-*.json       # Aggregate metrics
```

**Non-Fatal**: Campaign succeeds even if pull fails

**Code Reference**: src/agenteval/orchestration/campaign.py:460-501

______________________________________________________________________

### Phase 3: Auto-Generate HTML Dashboard (Lines 502-558)

**Component**: `DashboardService` (src/agenteval/application/dashboard_service.py)

**Trigger**: Automatic after auto-pull completes **Configuration**: `auto_generate_dashboard`
(default: `True`)

**What It Does**:

- Reads pulled JSON data
- Generates interactive HTML dashboards with Chart.js
- Creates multiple report types:
  - Main dashboard with campaign overview
  - Individual campaign detail pages
  - Executive summary with recommendations

**Output Structure**:

```
demo/evidence/reports/
├── dashboard.html                      # Main overview dashboard
├── campaign_<campaign_id>.html         # Detail pages
├── summary.html                        # Executive summary
└── SUMMARY.md                          # Markdown summary
```

**Features**:

- **Interactive Charts**: Campaign scores, metric breakdowns, turn trends
- **Drill-Down Analysis**: Click campaigns to see turn-by-turn details
- **Visual Indicators**: Color-coded scores and status badges
- **Responsive Design**: Works on mobile and desktop

**Technologies**:

- Jinja2 templates (src/agenteval/reporting/templates/)
- Chart.js for visualizations
- Bootstrap for styling

**Non-Fatal**: Campaign succeeds even if dashboard generation fails

**Code Reference**: src/agenteval/orchestration/campaign.py:502-558

______________________________________________________________________

### Phase 4: Auto-Generate Evidence Report (Lines 559-621)

**Component**: Markdown Dashboard (src/agenteval/reporting/dashboard.py)

**Trigger**: Automatic after HTML dashboard completes **Configuration**:
`auto_generate_evidence_report` (default: `True`)

**What It Does**:

- Collects campaign insights from pulled data
- Generates lightweight markdown reports
- Creates portfolio-level summaries

**Output Structure**:

```
demo/evidence/
├── dashboard.md              # Comprehensive evidence dashboard
└── live-demo-latest.md       # Compact summary table
```

**Features**:

- **Portfolio Snapshot**: Average scores across all campaigns
- **Campaign Details**: Per-campaign metrics and status
- **Failing Metrics**: Quick identification of problem areas
- **Evidence Links**: Direct links to JSON artifacts

**Use Cases**:

- Quick command-line review (`cat demo/evidence/dashboard.md`)
- Git-friendly documentation (plain text)
- Integration with documentation systems

**Non-Fatal**: Campaign succeeds even if evidence report generation fails

**Code Reference**: src/agenteval/orchestration/campaign.py:559-621

______________________________________________________________________

## Configuration Options

All auto-generation features can be controlled via environment variables or configuration:

```python
# src/agenteval/config.py

class ApplicationConfig(BaseSettings):
    # Auto-Pull Configuration
    auto_pull_results_to_local: bool = True
    local_results_output_dir: str = "outputs/campaign-results"

    # HTML Dashboard Configuration
    auto_generate_dashboard: bool = True
    dashboard_output_dir: str = "demo/evidence/reports"

    # Markdown Evidence Report Configuration
    auto_generate_evidence_report: bool = True
    evidence_report_output_dir: str = "demo/evidence"
```

**Environment Variables**:

```bash
# Disable specific features if needed
AUTO_PULL_RESULTS_TO_LOCAL=false
AUTO_GENERATE_DASHBOARD=false
AUTO_GENERATE_EVIDENCE_REPORT=false

# Customize output directories
LOCAL_RESULTS_OUTPUT_DIR=custom/results
DASHBOARD_OUTPUT_DIR=custom/dashboards
EVIDENCE_REPORT_OUTPUT_DIR=custom/evidence
```

______________________________________________________________________

## Complete Integration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Campaign Execution                                           │
│    - Initialize campaign                                        │
│    - Execute turns with persona/red team agents                 │
│    - Real-time evaluation with judge agents                     │
│    - Aggregate metrics and scoring                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. Auto-Pull Results ✅ (default: enabled)                      │
│    - Download DynamoDB data (campaigns, turns, evaluations)     │
│    - Download S3 reports (aggregate metrics)                    │
│    - Save to: outputs/campaign-results/<campaign_id>/           │
│    - Add "local_results_path" to report                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. Auto-Generate HTML Dashboard ✅ (default: enabled)           │
│    - Read pulled JSON data                                      │
│    - Generate interactive HTML with Chart.js                    │
│    - Create: dashboard.html, campaign_*.html, summary.html      │
│    - Save to: demo/evidence/reports/                            │
│    - Add "dashboard_files" and "dashboard_path" to report       │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. Auto-Generate Evidence Report ✅ (default: enabled)          │
│    - Collect campaign insights                                  │
│    - Generate markdown dashboard                                │
│    - Create: dashboard.md, live-demo-latest.md                  │
│    - Save to: demo/evidence/                                    │
│    - Add "evidence_reports" to report                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. Campaign Complete                                            │
│    - Return comprehensive report with all artifact locations    │
│    - User has immediate access to:                              │
│      • JSON data (outputs/campaign-results/)                    │
│      • Interactive HTML dashboards (demo/evidence/reports/)     │
│      • Markdown summaries (demo/evidence/)                      │
└─────────────────────────────────────────────────────────────────┘
```

______________________________________________________________________

## Report Artifact Locations

After a campaign completes, the final report includes references to all generated artifacts:

```json
{
  "campaign_id": "abc123...",
  "status": "completed",
  "aggregate_metrics": { ... },

  // Phase 2: Auto-Pull
  "local_results_path": "outputs/campaign-results/abc123...",

  // Phase 3: HTML Dashboard
  "dashboard_path": "demo/evidence/reports",
  "dashboard_files": {
    "html_dashboard": "demo/evidence/reports/dashboard.html",
    "html_campaign_abc123": "demo/evidence/reports/campaign_abc123.html",
    "html_summary": "demo/evidence/reports/summary.html",
    "markdown_summary": "demo/evidence/reports/SUMMARY.md"
  },

  // Phase 4: Evidence Report
  "evidence_reports": {
    "dashboard": "demo/evidence/dashboard.md",
    "summary": "demo/evidence/live-demo-latest.md"
  }
}
```

______________________________________________________________________

## Error Handling

All auto-generation phases are **non-fatal**:

- If auto-pull fails → Campaign still succeeds, warning logged
- If dashboard generation fails → Campaign still succeeds, warning logged
- If evidence report generation fails → Campaign still succeeds, warning logged

This ensures that infrastructure issues (network problems, disk space, etc.) don't fail evaluations.

**Logging**:

```
[INFO] Auto-pulling campaign results to outputs/campaign-results
[INFO] Auto-pulled 4 files to outputs/campaign-results/abc123
[INFO] Auto-generating dashboard for campaign abc123
[INFO] Auto-generated 4 dashboard files
[INFO] Auto-generating markdown evidence report for campaign abc123
[INFO] Auto-generated markdown evidence reports
```

______________________________________________________________________

## Components NOT Auto-Integrated

### Report Consolidator (Optional)

**Component**: `ReportConsolidator` (src/agenteval/application/report_consolidator.py)

**Why Not Integrated**:

- Makes additional LLM calls (expensive, slow)
- Uses Reporter Agent for AI-generated insights
- Better suited for on-demand generation
- Would significantly increase campaign completion time

**When to Use**:

- When you need AI-generated executive summaries
- For presentation-ready reports with natural language insights
- When cost and time are not constraints

**Manual Usage**:

```python
from agenteval.application.report_consolidator import ReportConsolidator

consolidator = ReportConsolidator(reporter_agent, config)
report = await consolidator.generate_report(results_bundle)
```

______________________________________________________________________

## Benefits of Full Integration

### 1. Seamless User Experience

- No manual steps after campaign completion
- All reports available immediately
- Multiple formats for different use cases

### 2. Complete Audit Trail

- JSON data for programmatic access
- HTML dashboards for visual analysis
- Markdown for documentation and git tracking

### 3. Flexibility

- Each component can be individually disabled
- Custom output directories
- Non-fatal errors ensure reliability

### 4. Production Ready

- Comprehensive error handling
- Detailed logging
- Performance optimized (no unnecessary LLM calls)

______________________________________________________________________

## Testing Integration

To verify all components are working:

```bash
# Run a test campaign
python demo/agenteval_chatbot_demo.py --region us-east-1

# Verify outputs
ls outputs/campaign-results/          # Should have campaign directories
ls demo/evidence/reports/              # Should have HTML dashboards
cat demo/evidence/dashboard.md         # Should show campaign summary
cat demo/evidence/live-demo-latest.md  # Should show compact table
```

______________________________________________________________________

## Summary

**Total Integrated Components**: 3 (Auto-Pull, HTML Dashboard, Evidence Report) **Default Status**:
All enabled **Error Handling**: Non-fatal (campaign succeeds regardless) **Output Formats**: JSON,
HTML, Markdown **Configuration**: Fully customizable via environment variables

All components work together to provide a comprehensive, automated evaluation workflow that
maximizes user experience while maintaining flexibility and reliability.
