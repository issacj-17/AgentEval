# AgentEval

**Multi-Agent AI Evaluation Platform with Trace-Based Root Cause Analysis**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **🏆 AWS AI Agent Global Hackathon 2025 Submission** **📖 For Judges**: See
> [SUBMISSION_GUIDE.md](SUBMISSION_GUIDE.md) for quick navigation and evaluation instructions

AgentEval is a comprehensive evaluation framework for GenAI applications featuring autonomous agents
that simulate users, perform security testing, and provide detailed evaluations with trace-based
root cause analysis.

## 🌟 Features

### Three Agent Types

1. **Persona Agents** - Simulate realistic user behaviors

   - **10 pre-configured personas** loaded from YAML library
   - Categories: Emotional, Professional, Accessibility, Educational, Security, Testing
   - **Hot-reloadable** - Add/edit personas without code changes
   - Multi-level memory system (preferences, facts, summaries)
   - Dynamic state tracking (frustration levels, goals)

1. **Red Team Agents** - Automated security testing

   - **20 attack patterns across 4 categories** (Injection, Jailbreak, Social Engineering, Encoding)
   - Hot-reloadable from YAML library
   - Evolutionary attack generation with shared knowledge base

1. **Judge Agents** - Comprehensive evaluation

   - 13 evaluation metrics (Quality, Safety, Agent-specific)
   - Multi-judge debate mechanism
   - Confidence scoring

### SECRET SAUCE: Trace-Based Root Cause Analysis

**The only platform that shows you exactly WHERE your GenAI application failed.**

- W3C Trace Context propagation
- AWS X-Ray integration
- Correlates evaluation scores with distributed traces
- Identifies root causes with actionable recommendations

### Evidence Insights Dashboard

- Generate a consolidated Markdown summary with `python -m agenteval.reporting.dashboard --latest`
  (add `PYTHONPATH=src` when running from source)
- Portfolio snapshot highlights overall scores, success rates, and failing metrics per campaign
- Drill-down sections link directly to S3 reports, DynamoDB snapshots, and logs pulled by
  `scripts/run-live-demo.sh`
- Ready to share with stakeholders and hackathon judges without navigating dozens of JSON files

## 🚀 Quick Start

### Installation with uv (Recommended)

1. Install the [uv](https://github.com/astral-sh/uv) package manager via your preferred method (e.g.
   `pipx install uv`).

1. Clone the repository and install dependencies in an isolated environment:

   ```bash
   git clone https://github.com/aws-agents/aws-agents.git
   cd aws-agents
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"
   ```

### Installation with pip

```bash
pip install -e ".[dev]"
```

### Configuration

1. Copy the environment template:

```bash
cp .env.example .env
```

2. Configure your AWS credentials in `.env`:

```env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

3. Set up Bedrock model access in AWS Console (see [Required Permissions](#required-aws-permissions)
   below)

### Required AWS Permissions

To run the live demo setup script (`scripts/setup-live-demo.sh`), your AWS IAM user or role needs
the following permissions:

#### **Core AWS Services**

**1. AWS Security Token Service (STS)**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

### Live Demo Workflow

AgentEval ships with a fully automated AWS validation script. A successful run will:

- Provision every required AWS resource (tables, buckets, event bus, Bedrock access checks).
- Execute persona and red-team campaigns against real Bedrock models.
- Pull DynamoDB exports, S3 results, and rendered or locally generated reports into
  `demo/evidence/pulled-reports/<timestamp>/`.
- Refresh the summary dashboard at `demo/evidence/live-demo-latest.md`, which links to every
  artefact for reviewers.
- Stream console output to `demo/evidence/live-demo-logs/run-<timestamp>.log` for auditability.
- Capture complete AWS X-Ray trace documents for each campaign in `demo/evidence/trace-reports/`.

Typical sequence:

```bash
# One-time provisioning
scripts/setup-live-demo.sh --region us-east-1

# Sanity check
scripts/check-aws-services.sh --region us-east-1

# Full demo (add --quick for dry runs, --auto-teardown for automatic cleanup)
scripts/run-live-demo.sh --region us-east-1

# When finished
scripts/teardown-live-demo.sh --region us-east-1 --force
```

> Tip: The summary markdown file is recreated on each run—feel free to commit it for judges, but
> avoid manual edits.

**2. Amazon DynamoDB**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:ListTables",
        "dynamodb:TagResource",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/agenteval-*"
    }
  ]
}
```

**3. Amazon S3**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:PutBucketTagging",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListAllMyBuckets"
      ],
      "Resource": [
        "arn:aws:s3:::agenteval-*",
        "arn:aws:s3:::agenteval-*/*"
      ]
    }
  ]
}
```

**4. Amazon EventBridge**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "events:CreateEventBus",
        "events:DescribeEventBus",
        "events:ListEventBuses",
        "events:TagResource",
        "events:PutEvents"
      ],
      "Resource": "arn:aws:events:*:*:event-bus/agenteval*"
    }
  ]
}
```

**5. Amazon Bedrock**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:*::foundation-model/anthropic.claude-haiku-4-5-20251001-v1:0",
        "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0"
      ]
    }
  ]
}
```

**6. AWS X-Ray (for tracing)**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetTraceSummaries",
        "xray:GetTraceGraph",
        "xray:BatchGetTraces"
      ],
      "Resource": "*"
    }
  ]
}
```

#### **Minimal IAM Policy (Combined)**

For convenience, here's a combined IAM policy with all required permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AgentEvalDemoPermissions",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "dynamodb:CreateTable",
        "dynamodb:DescribeTable",
        "dynamodb:ListTables",
        "dynamodb:TagResource",
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:PutBucketTagging",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListAllMyBuckets",
        "events:CreateEventBus",
        "events:DescribeEventBus",
        "events:ListEventBuses",
        "events:TagResource",
        "events:PutEvents",
        "bedrock:GetFoundationModel",
        "bedrock:ListFoundationModels",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "xray:PutTraceSegments",
        "xray:PutTelemetryRecords",
        "xray:GetTraceSummaries",
        "xray:GetTraceGraph",
        "xray:BatchGetTraces"
      ],
      "Resource": "*"
    }
  ]
}
```

#### **How to Apply Permissions**

1. **Using AWS IAM Console**:

   - Go to IAM → Users → Your User → Add Permissions
   - Choose "Create Policy" → JSON tab
   - Paste the combined policy above
   - Name it `AgentEvalDemoPolicy`

1. **Using AWS CLI**:

   ```bash
   # Save the policy to a file: agenteval-policy.json
   aws iam create-policy \
     --policy-name AgentEvalDemoPolicy \
     --policy-document file://agenteval-policy.json

   # Attach to your user
   aws iam attach-user-policy \
     --user-name YOUR_USERNAME \
     --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/AgentEvalDemoPolicy
   ```

1. **Enable Bedrock Models** (CRITICAL):

   - Go to AWS Bedrock Console: https://console.aws.amazon.com/bedrock/
   - Click "Model access" → "Manage model access"
   - Enable:
     - ✅ **Anthropic Claude Haiku 4.5** (`anthropic.claude-haiku-4-5-20251001-v1:0`) - Persona & Red
       Team agents (requires Bedrock inference profile access)
     - ✅ **Amazon Nova Pro** (`amazon.nova-pro-v1:0`) - Judge agent
   - Click "Request model access" (usually instant approval)

### Quick Demo

#### Option 1: Mock Demo (No AWS Required)

Fast validation without AWS credentials:

```bash
python demo/agenteval_demo_mock.py
```

- ✓ Validates all 7 product objectives
- ✓ < 1 minute execution time
- ✓ No cost

#### Option 2: Live AWS Demo

Complete end-to-end validation with real AWS services:

```bash
# Automated workflow: setup → demo → teardown
scripts/run-live-demo.sh --auto-teardown

# Or step-by-step:
scripts/setup-live-demo.sh          # Create AWS resources
scripts/run-live-demo.sh --region us-east-1  # Execute demo + collect artefacts
scripts/teardown-live-demo.sh --region us-east-1 --force  # Cleanup
```

- ✓ Real Bedrock API calls
- ✓ DynamoDB, S3, EventBridge, X-Ray
- ✓ ~5 minutes execution time
- ✓ ~$0.10-0.50 cost

After each run, review `demo/evidence/live-demo-latest.md` for direct links to all DynamoDB exports,
S3 results, rendered (or locally generated) reports, and trace archives captured during the demo.

See [LIVE_DEMO_GUIDE.md](LIVE_DEMO_GUIDE.md) for detailed instructions.

## ✅ Verification & Testing

All fixes and features have been verified with Claude Haiku 4.5 enabled. See the complete
verification report:

📄 **[CLAUDE_HAIKU_VERIFICATION.md](CLAUDE_HAIKU_VERIFICATION.md)** - Complete system verification
with:

- ✅ Claude Haiku 4.5 integration working
- ✅ No response echoing detected
- ✅ 87% overall quality score achieved
- ✅ All AWS services operational
- ✅ Complete turn-by-turn analysis

Additional documentation:

- **[LIVE_DEMO_GUIDE.md](LIVE_DEMO_GUIDE.md)** - Detailed live demo instructions
- **[QUICK_START_JUDGES.md](QUICK_START_JUDGES.md)** - Quick judge evaluation guide

______________________________________________________________________

## 📖 Usage

### Python API

```python
import agenteval

# Initialize clients
async with agenteval.get_bedrock_client() as bedrock:
    # Invoke Claude for persona simulation
    response = await bedrock.invoke_claude(
        prompt="I'm frustrated with this service!",
        system_prompt="You are a frustrated customer."
    )
    print(response["content"])

# Use tracing
with agenteval.trace_operation("custom_operation", user_id="123"):
    # Your code here - automatically traced
    pass

# Get current trace ID
trace_id = agenteval.get_current_trace_id()
print(f"Current trace: {trace_id}")
```

### Configuration

```python
from agenteval import settings

# Access configuration
print(f"AWS Region: {settings.aws.region}")
print(f"Bedrock Model: {settings.aws.bedrock_persona_model}")
print(f"Tracing Enabled: {settings.observability.enable_tracing}")
```

## 🏗️ Architecture

Interactive Mermaid diagram: [`architecture/diagram.md`](architecture/diagram.md)\
Render locally with [Mermaid Live Editor](https://mermaid.live/) or embed directly into docs.

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Web UI      │  │  SDK Client  │  │  CLI Tool    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                         │
│           FastAPI + OpenTelemetry Auto-Instrumentation           │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│  PERSONA AGENTS  │  │  RED TEAM AGENTS │  │   JUDGE AGENTS   │
│                  │  │                  │  │                  │
│ + Memory System  │  │ + Attack Library │  │ + Trace Analysis │
│ + Behavior Trees │  │ + Shared KB      │  │ + Root Cause     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
                  ┌────────────────────────┐
                  │   TARGET SYSTEM        │
                  │  (Customer's GenAI App)│
                  │  + OpenTelemetry       │
                  └────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  OBSERVABILITY LAYER (SECRET SAUCE)              │
│  ┌──────────────────────┐    ┌──────────────────────┐           │
│  │  OTel Collector      │───▶│   AWS X-Ray          │           │
│  │  + Trace Correlation │    │   + Root Cause       │           │
│  └──────────────────────┘    └──────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Dependency Injection Architecture

AgentEval uses a comprehensive dependency injection (DI) architecture for improved testability,
maintainability, and separation of concerns:

**Core Components:**

1. **DI Container** (`src/agenteval/container.py`)

   - Centralized dependency management
   - Lazy initialization with singleton pattern
   - Managed lifecycle (connect/close)
   - FastAPI integration via `Depends()`

1. **Agent Factories** (`src/agenteval/factories/`)

   - `PersonaAgentFactory` - Creates persona agents with validation
   - `RedTeamAgentFactory` - Creates red team agents with attack configuration
   - `JudgeAgentFactory` - Creates judge agents for evaluation
   - Factory Method pattern for testability

1. **Application Services** (`src/agenteval/application/`)

   - `CampaignService` - Campaign lifecycle management
   - `ReportService` - Multi-format report generation
   - Framework-agnostic business logic

**Benefits:**

- **Testability**: Easy to mock dependencies in tests
- **Maintainability**: Single source of truth for dependencies
- **Flexibility**: Swap implementations without changing code
- **Type Safety**: Full type hints with compile-time checking

**Example Usage:**

```python
from agenteval.container import Container, get_container

# Create container
container = Container()

# Get dependencies
dynamodb = container.dynamodb()
persona_factory = container.persona_factory()
campaign_service = container.campaign_service()

# Use with FastAPI
from agenteval.container import get_campaign_service
from fastapi import Depends

@app.post("/campaigns")
async def create_campaign(
    service: CampaignService = Depends(get_campaign_service)
):
    return await service.create_campaign(...)
```

## 🛠️ Development

### Setup Development Environment

```bash
# Run automated setup
./scripts/setup.sh

# Or manually:
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v --cov

# Run specific test suite
pytest tests/unit/ -v

# Run with coverage report
pytest --cov=agenteval --cov-report=html
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/

# Type check
mypy src/
```

## 📦 Project Structure

```
agenteval/
├── src/agenteval/           # Main package
│   ├── config.py            # Configuration management
│   ├── container.py         # DI Container (NEW)
│   ├── application/         # Application Services (NEW)
│   │   ├── campaign_service.py  # Campaign lifecycle
│   │   └── report_service.py    # Report generation
│   ├── factories/           # Agent Factories (NEW)
│   │   ├── base.py          # Factory base class
│   │   ├── persona_factory.py   # Persona creation
│   │   ├── redteam_factory.py   # Red team creation
│   │   └── judge_factory.py     # Judge creation
│   ├── aws/                 # AWS service clients
│   │   ├── bedrock.py       # Claude & Nova LLMs
│   │   ├── dynamodb.py      # State management (DI-enabled)
│   │   ├── s3.py            # Results storage (DI-enabled)
│   │   ├── xray.py          # Trace retrieval (DI-enabled)
│   │   └── eventbridge.py   # Events (DI-enabled)
│   ├── observability/       # Tracing infrastructure
│   │   └── tracer.py        # OpenTelemetry setup
│   ├── agents/              # Agent implementations
│   │   ├── base.py          # Base agent class
│   │   ├── persona_agent.py # Persona behaviors
│   │   ├── redteam_agent.py # Attack execution
│   │   └── judge_agent.py   # Evaluation
│   ├── persona/             # YAML-based persona library
│   │   └── library.py       # Persona management
│   ├── memory/              # Memory systems
│   ├── redteam/             # Attack library
│   ├── evaluation/          # Metrics & correlation
│   ├── orchestration/       # Campaign orchestration
│   │   └── campaign.py      # CampaignOrchestrator (DI-enabled)
│   ├── api/                 # REST API (DI-enabled routes)
│   │   ├── lifespan.py      # FastAPI lifecycle manager (NEW)
│   │   └── routes/          # API endpoints
│   └── cli/                 # CLI tool
├── personas/                # Persona definitions
│   └── library.yaml         # 10 pre-configured personas
├── tests/                   # Test suite
│   ├── conftest.py          # DI-aware fixtures (Enhanced)
│   ├── test_utils.py        # Mock builders (NEW)
│   ├── unit/                # Unit tests
│   └── integration/         # Integration tests
│       ├── test_campaign_service.py   # Service tests (NEW)
│       ├── test_report_service.py     # Service tests (NEW)
│       ├── test_agent_factories.py    # Factory tests (NEW)
│       └── test_orchestrator_with_factories.py  # DI tests (NEW)
├── infrastructure/          # Cloud infrastructure definitions
└── req-docs/                # Requirements documentation (BRD, PRD, TAD, etc.)
```

## 🔧 AWS Services Used

- **Amazon Bedrock** - Claude Haiku 4.5, Nova Pro for LLM inference
- **AWS X-Ray** - Distributed tracing for root cause analysis
- **Amazon DynamoDB** - Campaign state and knowledge base storage
- **Amazon S3** - Results and report storage
- **Amazon EventBridge** - Event-driven agent coordination
- **AWS ECS Fargate** - Container orchestration (deployment)

## 📊 Key Metrics

- **Evaluation Speed**: \<5 minutes for 100-turn conversation
- **Trace Correlation Accuracy**: >90% root cause identification
- **Agent Realism**: >85% realistic behavior
- **Attack Detection**: >95% OWASP LLM Top 10 coverage

## 📚 Documentation

- [Requirements Documentation](req-docs/) — Business, product, and technical specs
- [AUDIT_REPORT.md](AUDIT_REPORT.md) — Current architecture and quality assessment
- [Compliance Checklist](req-docs/COMPLIANCE_CHECKLIST.md) — Submission readiness
- [Judge Access Instructions](req-docs/JUDGE_ACCESS.md) — Credentials & smoke tests
- [Evaluation Demo Playbook](req-docs/TEST_DEMO_PLAYBOOK.md) — Live demo + test plan

## 🔐 Security & Secrets

- Use IAM roles or AWS Secrets Manager for credentials.
- `.env.example` provides placeholders only; do **not** store production secrets in flat files.
- To load secrets locally, prefer [`aws-vault`](https://github.com/99designs/aws-vault) or
  `aws sso login` followed by environment variable export.

## 🧾 Compliance Artifacts

- [LICENSE](LICENSE) (MIT)
- [NOTICE.md](NOTICE.md) & [ATTRIBUTIONS.md](ATTRIBUTIONS.md)
- [TEAM_INFO.md](req-docs/TEAM_INFO.md) & [CHANGE_LOG.md](req-docs/CHANGE_LOG.md)
- [SUBMISSION_FREEZE.md](req-docs/SUBMISSION_FREEZE.md) &
  [ASSET_LICENSES.md](req-docs/ASSET_LICENSES.md)

## 💬 Support

- **GitHub Issues**:
  [Report bugs or request features](https://github.com/aws-agents/aws-agents/issues)
- **Email**: team@agenteval.dev
- **Documentation**: [Full docs](https://agenteval.dev/docs)

## 🏆 Acknowledgments

- AWS for providing the hackathon platform
- Anthropic for Claude models
- OpenTelemetry community for observability standards
- FastAPI for the excellent web framework

______________________________________________________________________

**Built for AWS AI Agent Global Hackathon 2025**

Made with ❤️ by the AgentEval Team
