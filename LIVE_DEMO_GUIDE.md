# AgentEval Live Demo Guide

Complete guide for running AgentEval with real AWS services in a production-like environment.

## Table of Contents

1. [Overview](#overview)
1. [Prerequisites](#prerequisites)
1. [Quick Start](#quick-start)
1. [Detailed Workflow](#detailed-workflow)
1. [Cost Management](#cost-management)
1. [Troubleshooting](#troubleshooting)

______________________________________________________________________

## Overview

The AgentEval Live Demo validates the platform end-to-end using real AWS services:

- **AWS Bedrock**: Real LLM API calls for Persona, Red Team, and Judge agents
- **DynamoDB**: Persistent storage for campaigns, turns, and evaluations
- **S3**: Results and report storage with presigned URLs
- **EventBridge**: Event publishing and routing
- **X-Ray**: Distributed tracing and root cause analysis

**What gets tested:**

1. Multi-agent orchestration with real Bedrock models
1. State management in DynamoDB
1. Results storage in S3
1. Event publishing to EventBridge
1. Trace collection with X-Ray

______________________________________________________________________

## Prerequisites

### 1. AWS Account Setup

**Required**:

- Active AWS account
- AWS CLI configured with credentials
- Sufficient permissions for:
  - DynamoDB (CreateTable, PutItem, GetItem, Scan)
  - S3 (CreateBucket, PutObject, GetObject)
  - EventBridge (CreateEventBus, PutEvents)
  - Bedrock (InvokeModel)
  - X-Ray (PutTraceSegments)

**Verify AWS access**:

```bash
aws sts get-caller-identity
```

### 2. Bedrock Model Access

Enable required models in AWS Bedrock console:

1. Go to AWS Console → Bedrock → Model access
1. Request access to:
   - `anthropic.claude-haiku-4-5-20251001-v1:0` (Persona & Red Team agents)
   - `amazon.nova-pro-v1:0` (Judge agent)
1. Wait for approval (usually instant)

➡️ *No inference profile?* The setup script also configures fallback on-demand models
(`amazon.titan-text-lite-v1` and `amazon.titan-text-express-v1`) so the demo can run even if
Claude/Nova profiles are unavailable.

**Verify model access**:

```bash
aws bedrock list-foundation-models --region us-east-1
```

### 3. Python Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

______________________________________________________________________

## Quick Start

### Option 1: Automated Workflow (Recommended)

Complete setup, demo execution, and cleanup in one command:

```bash
# Full demo with automatic cleanup
scripts/run-live-demo.sh --auto-teardown

# Quick mode (campaigns created but not executed)
scripts/run-live-demo.sh --quick --auto-teardown
```

The runner now also downloads every campaign artefact and refreshes the reviewer dashboard at
`demo/evidence/live-demo-latest.md`. Share that file—and the corresponding timestamped folder under
`demo/evidence/pulled-reports/`—with judges or teammates for an instant post-run summary. Full X-Ray
traces are exported to `demo/evidence/trace-reports/` for profiling.

### Option 2: Manual Workflow

Step-by-step control over each phase:

```bash
# 1. Setup AWS infrastructure
scripts/setup-live-demo.sh --region us-east-1

# 2. Verify services are ready
scripts/check-aws-services.sh --region us-east-1

# 3. Run live demo + artefact collection
scripts/run-live-demo.sh --region us-east-1

# 4. Review outputs (auto-generated)
cat demo/evidence/live-demo-latest.md

# 4b. Inspect the run log (optional)
ls demo/evidence/live-demo-logs/

# 4c. Review trace archives
ls demo/evidence/trace-reports/

# 5. Cleanup resources
scripts/teardown-live-demo.sh --region us-east-1
```

> Prefer invoking the Python script directly? Run `python demo/agenteval_live_demo.py` and then call
> `scripts/pull-live-reports.py` to mirror the artefact collection that `scripts/run-live-demo.sh`
> performs automatically.

> Tip: `.env.live-demo` includes `DEMO_TARGET_URL` and `DEMO_FALLBACK_TARGET_URL`. The default
> points to `https://postman-echo.com/post`; update these values if you have a dedicated staging
> endpoint for your agent.

______________________________________________________________________

## Detailed Workflow

### Phase 1: Setup

**What it does**:

- Creates 4 DynamoDB tables (campaigns, turns, evaluations, attack-knowledge)
- Creates 2 S3 buckets (results, reports)
- Creates EventBridge event bus
- Verifies Bedrock model access
- Generates `.env.live-demo` configuration

**Command**:

```bash
scripts/setup-live-demo.sh --region us-east-1
```

**Expected output**:

```
================================================
  AgentEval Live Demo Setup
================================================

✓ AWS CLI configured (Account: 123456789012)
✓ Table agenteval-campaigns created and active
✓ Table agenteval-turns created and active
✓ Table agenteval-evaluations created and active
✓ Table agenteval-attack-knowledge created and active
✓ Bucket agenteval-results-123456789012 created
✓ Bucket agenteval-reports-123456789012 created
✓ Event bus agenteval created
✓ Bedrock model accessible: anthropic.claude-haiku-4-5-20251001-v1:0
✓ Bedrock model accessible: amazon.nova-pro-v1:0
✓ Configuration saved to .env.live-demo

================================================
  Setup Complete!
================================================
```

**Time**: ~2-3 minutes

**Cost**: $0 (setup itself is free)

______________________________________________________________________

### Phase 2: Verification

**What it does**:

- Checks all AWS resources are created and accessible
- Verifies connectivity to each service
- Reports any issues or warnings

**Command**:

```bash
scripts/check-aws-services.sh --region us-east-1
```

**Expected output**:

```
================================================
  AgentEval AWS Services Health Check
================================================

✓ AWS CLI configured (Account: 123456789012)
✓ DynamoDB: 4 tables found
✓ S3: 2 buckets found
✓ EventBridge bus: agenteval
✓ Bedrock: All 2 models accessible
✓ X-Ray: Service available

================================================
  Health Check Summary
================================================

✓ Healthy: 6
⚠ Warnings: 0
✗ Errors: 0
```

**Time**: ~10-15 seconds

______________________________________________________________________

### Phase 3: Live Demo Execution

#### Quick Mode (Recommended First Run)

Creates campaigns but doesn't execute them. Validates infrastructure only.

**Command**:

```bash
scripts/run-live-demo.sh --quick
```

**What happens**:

1. ✓ Connects to AWS services
1. ✓ Creates Persona campaign in DynamoDB
1. ✓ Creates Red Team campaign in DynamoDB
1. ✓ Stores sample results in S3
1. ✓ Publishes events to EventBridge
1. ✓ Validates X-Ray tracing setup

**Time**: ~30 seconds

**Cost**: ~$0.01-0.02

#### Full Mode (Complete Validation)

Executes campaigns with real Bedrock API calls.

**Command**:

```bash
scripts/run-live-demo.sh
```

**What happens**:

1. ✓ Connects to AWS services
1. ✓ Creates and **executes** Persona campaign (5 turns)
   - Real Bedrock API calls to Claude 3.5 Sonnet
   - Stores conversation turns in DynamoDB
   - Collects X-Ray traces
1. ✓ Creates and **executes** Red Team campaign (4 attacks)
   - Real security testing with Bedrock
   - Stores attack results in DynamoDB
   - Evaluates vulnerabilities with Judge agent
1. ✓ Stores comprehensive results in S3
1. ✓ Publishes completion events to EventBridge
1. ✓ Analyzes X-Ray traces for root cause analysis
1. ✓ Pulls DynamoDB/S3 artefacts locally and refreshes `demo/evidence/live-demo-latest.md`

**Time**: ~3-5 minutes

**Cost**: ~$0.10-0.50

**Example output**:

```
🚀 AGENTEVAL LIVE DEMO
   Production Environment with Real AWS Services

================================================================================
  VERIFYING AWS CONNECTIVITY
================================================================================

ℹ Testing DynamoDB connection...
✓ DynamoDB connected (region: us-east-1)
ℹ Testing S3 connection...
✓ S3 connected (bucket: agenteval-results-123456789012)
ℹ Testing EventBridge connection...
✓ EventBridge connected (bus: agenteval)
ℹ Testing X-Ray connection...
✓ X-Ray connected (tracing enabled)

================================================================================
  1. PERSONA AGENT - Real AWS Bedrock Execution
================================================================================

ℹ Creating persona campaign with config: {...}
✓ Campaign created: cmp-persona-abc123
ℹ Executing campaign turns (this may take 1-2 minutes)...
✓ Campaign execution completed!
  Turns completed: 5
  Turns stored in DynamoDB: 5

================================================================================
  2. RED TEAM AGENT - Security Testing with AWS Bedrock
================================================================================

ℹ Creating red team campaign with config: {...}
✓ Campaign created: cmp-redteam-xyz789
ℹ Executing security tests (this may take 1-2 minutes)...
✓ Security testing completed!
  Attacks executed: 4
  Vulnerabilities detected: 2

================================================================================
  3. RESULTS STORAGE - S3 Integration
================================================================================

ℹ Storing results for campaign: cmp-persona-abc123
✓ Results stored in S3: s3://agenteval-results-123456789012/campaigns/...
ℹ Generating campaign report...
✓ Report stored: s3://agenteval-reports-123456789012/campaigns/...
  Presigned URL generated (expires in 1 hour)

================================================================================
  4. EVENT PUBLISHING - EventBridge Integration
================================================================================

ℹ Publishing campaign event for: cmp-persona-abc123
✓ Campaign event published to EventBridge
  Event bus: agenteval
  Event type: campaign.completed
ℹ Publishing turn event...
✓ Turn event published

ℹ Pulling live demo artefacts into demo/evidence/pulled-reports/20251019T032317
✓ Results payloads downloaded for campaign cmp-persona-abc123
✓ Rendered reports downloaded for campaign cmp-persona-abc123
ℹ Detailed pull log stored at demo/evidence/pulled-reports/20251019T032317/pull-live-reports.log

================================================================================
  5. TRACE ANALYSIS - X-Ray Integration
================================================================================

ℹ Querying X-Ray for distributed traces...
✓ X-Ray tracing is enabled
  → Traces are being collected for:
    • Campaign creation and execution
    • Agent invocations (Persona, Red Team, Judge)
    • AWS service calls (Bedrock, DynamoDB, S3)
    • Root cause analysis correlation

================================================================================
  LIVE DEMO SUMMARY
================================================================================

✓ All AgentEval components validated with real AWS services!

✓ VALIDATED COMPONENTS:
  1. AWS Bedrock - LLM agents (Persona, Red Team, Judge)
  2. DynamoDB - Campaign and turn state management
  3. S3 - Results and report storage
  4. EventBridge - Event publishing and routing
  5. X-Ray - Distributed tracing (enabled)

📊 DEMO STATISTICS:
  Campaigns created: 2
  Region: us-east-1
  Environment: live-demo
  Duration: 187.3s

🎯 NEXT STEPS:
  1. View campaign data in DynamoDB:
     aws dynamodb scan --table-name agenteval-campaigns --region us-east-1

  2. Review local summary:
     open demo/evidence/live-demo-latest.md

  3. Check EventBridge events (if event archiving is enabled)

  4. Clean up resources:
     scripts/teardown-live-demo.sh
```

______________________________________________________________________

### Phase 4: Inspect Results (Optional)

**View campaigns in DynamoDB**:

```bash
aws dynamodb scan \
  --table-name agenteval-campaigns \
  --region us-east-1 \
  --output json | jq '.Items[0]'
```

**View turns for a campaign**:

```bash
aws dynamodb query \
  --table-name agenteval-turns \
  --key-condition-expression "PK = :pk AND begins_with(SK, :sk)" \
  --expression-attribute-values '{
    ":pk": {"S": "CAMPAIGN#cmp-persona-abc123"},
    ":sk": {"S": "TURN#"}
  }' \
  --region us-east-1
```

**List results in S3**:

```bash
aws s3 ls s3://agenteval-results-{ACCOUNT_ID}/campaigns/ --recursive
```

**Download a report**:

```bash
aws s3 cp \
  s3://agenteval-reports-{ACCOUNT_ID}/campaigns/cmp-persona-abc123/report.txt \
  ./demo-report.txt
```

**View X-Ray traces** (if enabled):

```bash
# Get recent traces
aws xray get-trace-summaries \
  --start-time $(date -u -v-1H '+%Y-%m-%dT%H:%M:%S' 2>/dev/null || date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%S') \
  --end-time $(date -u '+%Y-%m-%dT%H:%M:%S') \
  --region us-east-1
```

**Generate consolidated dashboard**:

```bash
PYTHONPATH=src .venv/bin/python -m agenteval.reporting.dashboard --latest
open demo/evidence/dashboard.md  # macOS (use xdg-open on Linux)
```

- Alternatively, add the CLI call to the tail of `scripts/run-live-demo.sh` so every run emits
  `demo/evidence/dashboard.md`.
- The dashboard includes a portfolio snapshot, failing metric summaries, latency notes, and direct
  links back to raw artefacts for auditors/judges.

______________________________________________________________________

### Phase 5: Cleanup

**Full cleanup (recommended)**:

```bash
scripts/teardown-live-demo.sh --region us-east-1
```

**Automatic cleanup (no prompts)**:

```bash
scripts/teardown-live-demo.sh --region us-east-1 --force
```

**Partial cleanup options**:

```bash
# Keep tables, delete data only
scripts/teardown-live-demo.sh --keep-tables

# Keep buckets, delete objects only
scripts/teardown-live-demo.sh --keep-buckets
```

**Verify cleanup**:

```bash
scripts/check-aws-services.sh --region us-east-1
```

**Expected output after cleanup**:

```
================================================
  Health Check Summary
================================================

✓ Healthy: 1
⚠ Warnings: 0
✗ Errors: 0
ℹ Not configured: 5

(All AgentEval resources have been removed)
```

______________________________________________________________________

## Cost Management

### Estimated Costs

| Operation             | Cost Range | Notes                      |
| --------------------- | ---------- | -------------------------- |
| **Setup**             | $0.00      | Resource creation is free  |
| **Quick Mode Demo**   | $0.01-0.02 | Minimal API calls          |
| **Full Demo**         | $0.10-0.50 | Includes Bedrock API calls |
| **Storage (ongoing)** | $0.001/day | If not cleaned up          |

### Cost Breakdown

**DynamoDB**:

- Pay-per-request pricing
- ~50-100 write requests per demo
- Cost: < $0.01

**S3**:

- Storage: ~1-2 MB total
- Requests: ~10-20 PUTs/GETs
- Cost: < $0.01

**EventBridge**:

- Free tier: 1M events/month
- Demo uses: ~10 events
- Cost: $0.00

**Bedrock** (Full Mode Only):

- Claude 3.5 Sonnet: $3 per 1M input tokens
- Demo usage: ~5-10k tokens
- Cost: $0.05-0.15

**X-Ray**:

- Free tier: 100k traces/month
- Demo uses: ~50-100 traces
- Cost: $0.00

### Minimizing Costs

1. **Use Quick Mode for testing**:

   ```bash
   scripts/run-live-demo.sh --quick
   ```

1. **Always run teardown**:

   ```bash
   scripts/teardown-live-demo.sh --force
   ```

1. **Use automated workflow**:

   ```bash
   scripts/run-live-demo.sh --quick --auto-teardown
   ```

1. **Monitor costs**:

   ```bash
   aws ce get-cost-and-usage \
     --time-period Start=2024-01-01,End=2024-01-31 \
     --granularity MONTHLY \
     --metrics BlendedCost
   ```

______________________________________________________________________

## Troubleshooting

### Common Issues

#### 1. "AWS CLI not configured"

**Symptom**:

```
✗ AWS CLI not configured or credentials invalid
```

**Solution**:

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key_id
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=us-east-1
```

______________________________________________________________________

#### 2. "Bedrock model not accessible"

**Symptom**:

```
⚠ Bedrock model NOT accessible: anthropic.claude-haiku-4-5-20251001-v1:0 (requires Bedrock inference profile approval)
```

**Solution**:

1. Go to AWS Console → Bedrock → Model access
1. Request access to required models
1. Wait for approval (usually instant)
1. Re-run setup: `scripts/setup-live-demo.sh`

______________________________________________________________________

#### 3. "Table already exists"

**Symptom**:

```
⚠ Table agenteval-campaigns already exists
```

**Solution**: This is normal if you've run setup before. Options:

- Continue with demo (tables will be reused)
- Or clean up first: `scripts/teardown-live-demo.sh`

______________________________________________________________________

#### 4. "Demo execution timeout"

**Symptom**: Demo hangs during Bedrock API calls

**Solution**:

```bash
# Use quick mode instead
scripts/run-live-demo.sh --quick

# Or check Bedrock quotas
aws service-quotas get-service-quota \
  --service-code bedrock \
  --quota-code L-C0CE6F8B \
  --region us-east-1
```

______________________________________________________________________

#### 5. "Insufficient permissions"

**Symptom**:

```
An error occurred (AccessDeniedException) when calling the...
```

**Solution**: Ensure your AWS user/role has permissions for:

- `dynamodb:CreateTable`, `dynamodb:PutItem`, `dynamodb:GetItem`
- `s3:CreateBucket`, `s3:PutObject`, `s3:GetObject`
- `events:CreateEventBus`, `events:PutEvents`
- `bedrock:InvokeModel`, `bedrock:GetFoundationModel`
- `xray:PutTraceSegments`

______________________________________________________________________

#### 6. "No module named 'agenteval'"

**Symptom**:

```
ModuleNotFoundError: No module named 'agenteval'
```

**Solution**:

```bash
# Install in development mode
pip install -e ".[dev]"

# Or add src to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

______________________________________________________________________

### Getting Help

**Check service status**:

```bash
scripts/check-aws-services.sh --json | jq .
```

**View logs**:

```bash
# Python logging (if enabled)
tail -f agenteval.log

# CloudWatch logs (if configured)
aws logs tail /aws/agenteval/live-demo --follow
```

**Verify configuration**:

```bash
cat .env.live-demo
```

______________________________________________________________________

## Best Practices

1. **Always run setup first**:

   ```bash
   scripts/setup-live-demo.sh
   ```

1. **Use quick mode for initial validation**:

   ```bash
   scripts/run-live-demo.sh --quick
   ```

1. **Always clean up after demo**:

   ```bash
   scripts/teardown-live-demo.sh --force
   ```

1. **Use automated workflow for repeated runs**:

   ```bash
   scripts/run-live-demo.sh --quick --auto-teardown
   ```

1. **Monitor costs regularly**:

   ```bash
   aws ce get-cost-and-usage --time-period ...
   ```

1. **Keep .env.live-demo secure**:

   ```bash
   # Add to .gitignore
   echo ".env.live-demo" >> .gitignore
   ```

______________________________________________________________________

## Next Steps

After successful live demo:

1. ✓ Review results in DynamoDB and S3
1. ✓ Check X-Ray traces for performance insights
1. ✓ Customize demo for your use case
1. ✓ Integrate into CI/CD pipeline
1. ✓ Deploy production version

For production deployment, see:

- `docs/deployment.md`
- `docs/production-checklist.md`
- `scripts/deploy.sh`

______________________________________________________________________

## Support

For issues or questions:

1. Review this guide
1. Check `scripts/check-aws-services.sh` output
1. Review CloudWatch logs
1. Consult main README.md
1. Open GitHub issue with debug info
