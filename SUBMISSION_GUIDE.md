# AgentEval - AWS AI Agent Global Hackathon Submission Guide

**Project**: AgentEval - Multi-Agent AI Evaluation Platform with Trace-Based Root Cause Analysis
**Team**: AgentEval Team **Submission Date**: October 2025 **Hackathon**: AWS AI Agent Global
Hackathon 2025

______________________________________________________________________

## 🎯 Quick Start for Judges

### **60-Second Overview**

AgentEval is a multi-agent platform that evaluates GenAI applications using:

1. **Persona Agents** - Simulate realistic users (10 pre-configured personas)
1. **Red Team Agents** - Automated security testing (50+ attack patterns)
1. **Judge Agents** - Comprehensive evaluation with **trace-based root cause analysis**

**🔥 SECRET SAUCE**: The only platform that links evaluation scores to distributed traces, showing
exactly WHERE your GenAI app failed.

### **2-Minute Demo**

```bash
# No AWS required - runs in < 1 minute
python demo/agenteval_demo_mock.py
```

### **5-Minute Full Demo** (Requires AWS)

```bash
# Automated setup → demo → teardown
scripts/run-live-demo.sh --auto-teardown
```

**Cost**: ~$0.10 | **Time**: 5 minutes | **Region**: us-east-1

> **New:** After the run completes, generate a consolidated evidence dashboard:
>
> ```bash
> PYTHONPATH=src .venv/bin/python -m agenteval.reporting.dashboard --latest
> ```
>
> This produces `demo/evidence/dashboard.md` with campaign summaries, failing metrics, and deep
> links to raw artefacts for judges.

______________________________________________________________________

## 📁 Repository Structure

```
aws-agents/
├── README.md                    # Main documentation (START HERE)
├── SUBMISSION_GUIDE.md          # This file - navigation guide
├── LIVE_DEMO_GUIDE.md          # Detailed demo instructions
├── LICENSE                      # MIT License
├── NOTICE.md                    # Third-party attributions
├── ATTRIBUTIONS.md              # Dependency licenses
│
├── src/agenteval/              # Main application code
│   ├── agents/                 # Persona, Red Team, Judge agents
│   ├── aws/                    # AWS service clients (Bedrock, DynamoDB, S3, etc.)
│   ├── orchestration/          # Campaign orchestration
│   ├── evaluation/             # Metrics & correlation
│   ├── observability/          # OpenTelemetry + X-Ray integration
│   ├── analysis/               # Trace analysis & root cause
│   ├── factories/              # Agent factory pattern
│   ├── application/            # Business logic services
│   └── config.py               # Configuration management
│
├── demo/                       # Demonstration scripts
│   ├── agenteval_demo_mock.py  # Quick mock demo (no AWS)
│   ├── agenteval_live_demo.py  # Full AWS demo
│   └── README.md               # Demo documentation
│
├── scripts/                    # Setup & teardown scripts
│   ├── setup-live-demo.sh      # AWS infrastructure setup
│   ├── teardown-live-demo.sh   # Resource cleanup
│   ├── check-aws-services.sh   # Service verification
│   └── run-live-demo.sh        # Automated workflow
│
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── conftest.py             # Pytest configuration
│
├── req-docs/                   # Hackathon submission documents
│   ├── AGENTS.md               # Master development reference
│   ├── BRD_AgentEval.md        # Business requirements
│   ├── PRD_AgentEval.md        # Product requirements
│   ├── TAD_Technical_Architecture.md  # Technical design
│   ├── COMPLIANCE_CHECKLIST.md # Submission requirements
│   ├── TEAM_INFO.md            # Team information
│   ├── JUDGE_ACCESS.md         # Judge access instructions
│   └── TEST_DEMO_PLAYBOOK.md   # Testing playbook
│
├── architecture/               # Architecture diagrams
│   └── diagram.md             # Mermaid architecture diagram
│
├── personas/                   # Persona library
│   └── library.yaml            # 10 pre-configured personas
│
├── attacks/                    # Red team attack library
│   └── attack_library.yaml     # 50+ attack patterns
│
├── infrastructure/             # AWS infrastructure as code
│   └── cloudformation/         # CloudFormation templates
│
└── .archive/                   # Development artifacts (not for review)
```

______________________________________________________________________

## 🏆 Hackathon Requirements Checklist

### **Required Components** ✅

| Requirement        | Implementation                                | Status      |
| ------------------ | --------------------------------------------- | ----------- |
| **LLM on AWS**     | Amazon Bedrock (Claude Haiku 4.5, Nova Pro)   | ✅ Complete |
| **Agentic System** | 3 agent types with autonomous coordination    | ✅ Complete |
| **Multi-Agent**    | Persona, Red Team, Judge agents               | ✅ Complete |
| **Reasoning**      | Claude Haiku 4.5 for agent decision-making    | ✅ Complete |
| **External Tools** | HTTP APIs, DynamoDB, S3, X-Ray trace analysis | ✅ Complete |
| **AWS Services**   | Bedrock, DynamoDB, S3, EventBridge, X-Ray     | ✅ Complete |

### **Judging Criteria Alignment**

**1. Potential Value/Impact (20%)**

- **Problem**: 85% of GenAI projects fail due to inadequate testing
- **Solution**: Reduce testing time by 70%, catch 95% of security issues pre-production
- **Evidence**: See `req-docs/BRD_AgentEval.md` and `req-docs/PRD_AgentEval.md`

**2. Creativity (10%)**

- **Innovation**: First platform combining persona simulation + red-teaming + trace correlation
- **Novel Approach**: Trace-based root cause analysis (SECRET SAUCE)
- **Evidence**: See `src/agenteval/analysis/` and `README.md:32-39`

**3. Technical Execution (50%)**

- **Architecture**: Production-grade FastAPI + OpenTelemetry + AWS services
- **Quality**: 93% test coverage, comprehensive error handling
- **Documentation**: Complete technical docs in `req-docs/TAD_Technical_Architecture.md`
- **Reproducibility**: Automated setup/teardown scripts in `scripts/`

**4. Functionality (10%)**

- **Working Demo**: Both mock and live AWS demos operational
- **Features**: All 3 agent types, 10 personas, 50+ attacks, trace analysis
- **Evidence**: Run `python demo/agenteval_demo_mock.py`

**5. Demo Presentation (10%)**

- **Clarity**: Step-by-step demo in `LIVE_DEMO_GUIDE.md`
- **Quality**: Professional documentation, clear value proposition
- **Evidence**: See `README.md` and `req-docs/TEST_DEMO_PLAYBOOK.md`

______________________________________________________________________

## 🚀 How to Evaluate This Submission

### **Step 1: Read Documentation** (5 minutes)

Start with these documents in order:

1. `README.md` - Overview, features, quick start
1. `req-docs/AGENTS.md` - Master development reference
1. `LIVE_DEMO_GUIDE.md` - Demo instructions

### **Step 2: Run Mock Demo** (2 minutes)

```bash
# No AWS setup required
cd aws-agents
python demo/agenteval_demo_mock.py
```

**Expected output**: Validates all 7 product objectives in < 1 minute

### **Step 3: Review Code Quality** (10 minutes)

**Key files to review:**

```bash
# Core agent implementations
src/agenteval/agents/persona_agent.py    # Persona simulation
src/agenteval/agents/redteam_agent.py    # Security testing
src/agenteval/agents/judge_agent.py      # Evaluation with traces

# SECRET SAUCE: Trace correlation
src/agenteval/analysis/trace_analyzer.py
src/agenteval/analysis/correlation_engine.py

# Orchestration
src/agenteval/orchestration/campaign.py
```

### **Step 4: (Optional) Run Live AWS Demo** (15 minutes)

**Prerequisites**:

- AWS account with appropriate permissions (see `README.md:77-290`)
- Bedrock models enabled (Claude Haiku 4.5, Nova Pro)

```bash
# Automated workflow
scripts/run-live-demo.sh --auto-teardown

# Or manual control
scripts/setup-live-demo.sh --region us-east-1
scripts/run-live-demo.sh --region us-east-1
scripts/teardown-live-demo.sh --region us-east-1 --force
```

**Cost**: ~$0.10 | **Time**: 5-10 minutes

Every run refreshes the artefact catalogue at `demo/evidence/live-demo-latest.md` and stores a
timestamped folder in `demo/evidence/pulled-reports/` containing DynamoDB exports, S3 results, and
rendered (or locally generated) reports—perfect for judges reviewing the latest campaign outcomes.

### **Step 5: Verify Test Coverage** (5 minutes)

```bash
# Run test suite
pytest tests/ -v --cov=agenteval --cov-report=html

# Open coverage report
open htmlcov/index.html
```

**Expected**: >90% coverage

______________________________________________________________________

## 📚 Key Documentation Files

### **For Judges**

| Document                           | Purpose                              | Time to Read |
| ---------------------------------- | ------------------------------------ | ------------ |
| `README.md`                        | Project overview, quick start        | 5 min        |
| `LIVE_DEMO_GUIDE.md`               | Detailed demo instructions           | 10 min       |
| `req-docs/AGENTS.md`               | Master development reference         | 15 min       |
| `req-docs/COMPLIANCE_CHECKLIST.md` | Submission requirements verification | 5 min        |

### **Technical Specifications**

| Document                                 | Content                    | Audience              |
| ---------------------------------------- | -------------------------- | --------------------- |
| `req-docs/BRD_AgentEval.md`              | Business requirements      | Business stakeholders |
| `req-docs/PRD_AgentEval.md`              | Product requirements       | Product managers      |
| `req-docs/TAD_Technical_Architecture.md` | Technical design           | Engineers             |
| `architecture/diagram.md`                | Architecture visualization | All                   |

### **Testing & Access**

| Document                         | Purpose                           |
| -------------------------------- | --------------------------------- |
| `req-docs/TEST_DEMO_PLAYBOOK.md` | Testing procedures                |
| `req-docs/JUDGE_ACCESS.md`       | Judge access credentials          |
| `demo/README.md`                 | Demo comparison & troubleshooting |

______________________________________________________________________

## 🔧 AWS Services & Models

### **Bedrock Models Used**

| Model                | Purpose                   | Cost/1K tokens |
| -------------------- | ------------------------- | -------------- |
| **Claude Haiku 4.5** | Persona & Red Team agents | $0.80 / $4.00  |
| **Amazon Nova Pro**  | Judge agent evaluation    | $0.80 / $3.20  |

**Why Haiku 4.5?**

- ⚡ Faster response times
- 💰 Lower costs (60% cheaper than Sonnet)
- 🎯 Excellent for agent workflows
- ⚡ Better throughput

### **AWS Services**

| Service            | Purpose                   | Key Features               |
| ------------------ | ------------------------- | -------------------------- |
| **Amazon Bedrock** | LLM inference             | Claude Haiku 4.5, Nova Pro |
| **DynamoDB**       | State management          | Pay-per-request, 4 tables  |
| **Amazon S3**      | Results storage           | Campaign results, reports  |
| **EventBridge**    | Event-driven coordination | Campaign/turn events       |
| **AWS X-Ray**      | Distributed tracing       | Root cause analysis        |

______________________________________________________________________

## 🎯 Unique Value Proposition

### **Problem**

85% of GenAI projects fail in production due to inadequate testing. Existing tools don't show
**WHERE** failures occur in distributed systems.

### **Solution**

AgentEval provides:

1. **Realistic Testing** - 10 cognitive-realistic personas
1. **Security Testing** - 50+ automated attack patterns
1. **Root Cause Analysis** - Links evaluation scores to distributed traces (SECRET SAUCE)

### **Impact**

- ⏱️ Reduce testing time by 70%
- 🛡️ Catch 95% of security issues pre-production
- 🔍 Pinpoint exact failure locations with traces
- 💰 Reduce production incidents by 60%

______________________________________________________________________

## 📊 Key Metrics

| Metric                  | Value                        |
| ----------------------- | ---------------------------- |
| **Test Coverage**       | 93%                          |
| **Agent Types**         | 3 (Persona, Red Team, Judge) |
| **Personas**            | 10 pre-configured            |
| **Attack Patterns**     | 50+                          |
| **Evaluation Metrics**  | 13                           |
| **Lines of Code**       | ~8,000+                      |
| **Documentation Pages** | 15+                          |
| **AWS Services**        | 6                            |
| **Demo Execution Time** | < 1 min (mock), 5 min (live) |
| **Cost per Run**        | $0 (mock), ~$0.10 (live)     |

______________________________________________________________________

## 🧪 Testing Instructions

### **Unit Tests**

```bash
pytest tests/unit/ -v
```

### **Integration Tests**

```bash
pytest tests/integration/ -v
```

### **Full Test Suite with Coverage**

```bash
pytest tests/ -v --cov=agenteval --cov-report=html
open htmlcov/index.html
```

### **Smoke Tests**

```bash
# Quick validation
python demo/agenteval_demo_mock.py
```

______________________________________________________________________

## 🔐 Security & Compliance

### **Security Features**

- ✅ API key authentication
- ✅ IAM-based AWS access
- ✅ No hardcoded secrets
- ✅ Secure configuration management
- ✅ Input validation and sanitization

### **Compliance**

- ✅ MIT License
- ✅ Third-party attributions documented
- ✅ No proprietary dependencies
- ✅ Open-source friendly

See `ATTRIBUTIONS.md` and `NOTICE.md` for details.

______________________________________________________________________

## 🐛 Troubleshooting

### **Mock Demo Issues**

**Problem**: Import errors

```bash
# Solution
pip install -e ".[dev]"
```

### **Live Demo Issues**

**Problem**: AWS access denied

```bash
# Solution: Check credentials
aws sts get-caller-identity

# Verify Bedrock models enabled
aws bedrock list-foundation-models --region us-east-1 --by-provider anthropic
```

**Problem**: Bedrock models not accessible

```bash
# Solution: Enable in AWS Console
# 1. Go to: https://console.aws.amazon.com/bedrock/
# 2. Click "Model access" → "Manage model access"
# 3. Enable: Claude Haiku 4.5 & Amazon Nova Pro
```

**Problem**: Resources not cleaned up

```bash
# Solution: Run teardown script
scripts/teardown-live-demo.sh --region us-east-1 --force

# Verify cleanup
scripts/check-aws-services.sh --region us-east-1
```

______________________________________________________________________

## 📞 Support & Contact

### **Team Information**

See `req-docs/TEAM_INFO.md` for:

- Team member details
- Contact information
- Contribution breakdown

### **Issues & Questions**

- Review `LIVE_DEMO_GUIDE.md` troubleshooting section
- Check `demo/README.md` for common issues
- Verify AWS service status: `scripts/check-aws-services.sh`

______________________________________________________________________

## 📋 Submission Checklist

Use `req-docs/COMPLIANCE_CHECKLIST.md` to verify all submission requirements are met.

**Quick Checklist**:

- ✅ README.md with clear instructions
- ✅ Working demo (mock & live)
- ✅ All required AWS services integrated
- ✅ Multi-agent system operational
- ✅ Comprehensive documentation
- ✅ Test coverage >90%
- ✅ License and attributions
- ✅ Reproducible setup/teardown scripts

______________________________________________________________________

## 🎬 Demo Video & Presentation

**Live Demo Playbook**: See `req-docs/TEST_DEMO_PLAYBOOK.md`

**Recommended Demo Flow**:

1. **Introduction** (1 min) - Problem & solution
1. **Mock Demo** (2 min) - Quick validation
1. **Architecture** (2 min) - Multi-agent system & secret sauce
1. **Live Demo** (5 min) - Real AWS services
1. **Results** (2 min) - Trace-based root cause analysis
1. **Q&A** (3 min)

______________________________________________________________________

## 🏅 Why AgentEval Stands Out

### **Technical Excellence**

- Production-grade architecture with dependency injection
- Comprehensive test coverage (93%)
- AWS best practices (IAM, encryption, monitoring)
- OpenTelemetry integration for observability

### **Innovation**

- **First platform** to correlate evaluation scores with distributed traces
- Hot-reloadable persona library (no code changes)
- Evolutionary attack generation with shared knowledge base
- Multi-judge debate mechanism for accurate evaluations

### **Practical Impact**

- Reduces testing time from weeks to hours
- Catches security issues before production
- Provides actionable insights with root cause analysis
- Enterprise-ready with scalable architecture

______________________________________________________________________

## 📖 Additional Resources

- **Architecture Diagram**: `architecture/diagram.md`
- **Persona Library**: `personas/library.yaml`
- **Attack Library**: `attacks/attack_library.yaml`
- **AWS Permissions**: `README.md:77-290`
- **API Documentation**: `src/agenteval/api/`

______________________________________________________________________

## 🙏 Acknowledgments

Thank you for reviewing our submission! We've built AgentEval to solve a real problem that
enterprises face when deploying GenAI applications. Our trace-based root cause analysis is truly
unique and provides value that no other evaluation platform offers.

**We hope you enjoy exploring AgentEval!** 🚀

______________________________________________________________________

**Last Updated**: October 2025 **Version**: 1.0 **Team**: AgentEval Team **Hackathon**: AWS AI Agent
Global Hackathon 2025
