# AgentEval Demo Applications

This directory contains demonstration applications for AgentEval functionality.

## Available Demos

### 1. Mock Demo (`agenteval_demo_mock.py`)

**Purpose**: Validates AgentEval architecture and objectives using simulated components

**Features**:
- No AWS credentials required
- Fast execution (< 1 minute)
- Validates all 7 product objectives
- Tests Persona, Red Team, and Judge agents
- Demonstrates trace-based root cause analysis

**Usage**:
```bash
python demo/agenteval_demo_mock.py
```

**When to use**:
- Development and testing
- CI/CD pipelines
- Architecture validation
- Quick functionality verification

---

### 2. Live AWS Demo (`agenteval_live_demo.py`)

**Purpose**: End-to-end validation with real AWS services in production-like environment

**Features**:
- Uses real AWS Bedrock for LLM agents
- Stores data in DynamoDB
- Saves results to S3
- Publishes events to EventBridge
- Collects traces with X-Ray
- Full production workflow

**Prerequisites**:
```bash
# 1. AWS credentials configured
aws configure

# 2. Run setup script
scripts/setup-live-demo.sh --region us-east-1

# 3. Verify services
scripts/check-aws-services.sh
```

**Usage**:
```bash
# Full demo (creates and executes campaigns)
python demo/agenteval_live_demo.py

# Quick mode (creates campaigns only, no execution)
python demo/agenteval_live_demo.py --quick
```

**Automated workflow**:
```bash
# Complete workflow: setup → demo → teardown
scripts/run-live-demo.sh --region us-east-1 --auto-teardown

# Quick demo without execution
scripts/run-live-demo.sh --quick
```

**When to use**:
- Pre-production validation
- Integration testing with AWS
- Performance testing
- End-to-end verification

---

### 3. Chatbot AWS Demo (`agenteval_chatbot_demo.py`)

**Purpose**: Launch the bundled FastAPI banking assistant locally and exercise it with real Bedrock agents + inference profiles. This mirrors the live demo workflow but against a richer, stateful target.

**Features**:
- Spins up `examples/demo_chatbot` automatically (or attaches to an existing instance)
- Reuses the Bedrock inference profile ARNs from `.env.live-demo`
- Runs persona + red-team campaigns, publishes events, stores artefacts, and annotates echo replies in the logs
- Supports `--auto-teardown` to clean up AWS resources afterwards

**Usage**:
```bash
# Ensure setup has run and .env.live-demo is populated
scripts/setup-live-demo.sh --region us-east-1

# Run the advanced demo against the local chatbot
python demo/agenteval_chatbot_demo.py --region us-east-1 --auto-teardown

# The script prints the models + inference profile ARNs in use.
```

**When to use**:
- Scenario testing with a realistic chatbot surface
- Demonstrating inference profile usage end-to-end
- Building custom playbooks around the demo FastAPI service

---

## Demo Comparison

| Feature | Mock Demo | Live AWS Demo |
|---------|-----------|---------------|
| **Execution Time** | < 1 minute | 3-5 minutes |
| **AWS Required** | ❌ No | ✅ Yes |
| **Cost** | Free | ~$0.10-0.50 |
| **Bedrock Calls** | Simulated | Real API calls |
| **Data Persistence** | In-memory | DynamoDB + S3 |
| **Tracing** | Simulated | Real X-Ray |
| **Use Case** | Development | Pre-production |

---

## Quick Start

### Option 1: Mock Demo (Fastest)
```bash
# No setup required
python demo/agenteval_demo_mock.py
```

### Option 2: Live AWS Demo (Full Validation)
```bash
# One-time setup
scripts/setup-live-demo.sh

# Run demo
python demo/agenteval_live_demo.py

# Cleanup when done
scripts/teardown-live-demo.sh
```

### Option 3: Automated Workflow
```bash
# Complete setup → demo → teardown
scripts/run-live-demo.sh --auto-teardown
```

---

## Output Examples

### Mock Demo Output
```
🚀 AGENTEVAL COMPREHENSIVE DEMO
================================================================================
  1. PERSONA AGENT - Simulating Realistic User Behavior
================================================================================
✓ Persona Agent evaluation complete
ℹ Tested 2 personas with 6 interactions
...
```

### Live AWS Demo Output
```
🚀 AGENTEVAL LIVE DEMO - Real AWS Services
================================================================================
  VERIFYING AWS CONNECTIVITY
================================================================================
✓ DynamoDB connected (region: us-east-1)
✓ S3 connected (bucket: agenteval-results-123456789)
✓ EventBridge connected (bus: agenteval)
...
```

---

## Troubleshooting

### Mock Demo Issues

**Problem**: Import errors
```bash
# Solution: Install dependencies
pip install -e ".[dev]"
```

### Live AWS Demo Issues

**Problem**: AWS connectivity errors
```bash
# Solution: Verify credentials and setup
aws sts get-caller-identity
scripts/check-aws-services.sh
```

**Problem**: Bedrock access denied
```bash
# Solution: Enable models in AWS Console
# Go to: AWS Console → Bedrock → Model access → Request access
```

**Problem**: Demo hangs during execution
```bash
# Run in quick mode instead
python demo/agenteval_live_demo.py --quick
```

---

## Cleanup

### Mock Demo
No cleanup needed (no persistent resources)

### Live AWS Demo
```bash
# Remove all AWS resources
scripts/teardown-live-demo.sh

# Verify cleanup
scripts/check-aws-services.sh
```

---

## Advanced Usage

### Custom Configuration

Create `.env.live-demo` with custom settings:
```bash
AWS_REGION=us-west-2
AWS_BEDROCK_PERSONA_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0
AWS_BEDROCK_REDTEAM_MODEL=anthropic.claude-haiku-4-5-20251001-v1:0
AWS_BEDROCK_JUDGE_MODEL=amazon.nova-pro-v1:0
```

### Partial Cleanup

Keep DynamoDB tables but delete data:
```bash
scripts/teardown-live-demo.sh --keep-tables
```

Keep S3 buckets but delete objects:
```bash
scripts/teardown-live-demo.sh --keep-buckets
```

---

## Cost Estimation

### Mock Demo
- **Cost**: $0 (no AWS usage)

### Live AWS Demo (Quick Mode)
- **Estimated**: $0.01-0.05
- DynamoDB: Pay-per-request (minimal writes)
- S3: Storage + requests (< 1 MB)
- EventBridge: Free tier
- X-Ray: Free tier (< 100k traces/month)

### Live AWS Demo (Full Execution)
- **Estimated**: $0.10-0.50
- Additional Bedrock API calls:
  - Persona: ~$0.01-0.05 per campaign
  - Red Team: ~$0.01-0.05 per campaign
  - Judge: ~$0.01-0.03 per evaluation

**Note**: Costs vary by region and usage. Always run `teardown-live-demo.sh` when finished to avoid ongoing charges.

---

## Support

For issues or questions:
1. Check `scripts/check-aws-services.sh` output
2. Review AWS CloudWatch logs
3. Verify `.env.live-demo` configuration
4. Consult main repository README.md
