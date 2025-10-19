# Repository Organization Summary

**Last Updated**: October 2025 **Status**: Submission-Ready **Hackathon**: AWS AI Agent Global
Hackathon 2025

______________________________________________________________________

## 📋 Current Repository Structure

```
aws-agents/
├── 📄 Core Documentation
│   ├── README.md                    ★ START HERE - Main documentation
│   ├── SUBMISSION_GUIDE.md          ★ FOR JUDGES - Navigation & evaluation guide
│   ├── LIVE_DEMO_GUIDE.md          Detailed live demo instructions
│   ├── LICENSE                      MIT License
│   ├── NOTICE.md                    Third-party notices
│   └── ATTRIBUTIONS.md              Dependency licenses
│
├── 📦 Source Code
│   └── src/agenteval/              Main application code
│       ├── agents/                 Agent implementations (Persona, Red Team, Judge)
│       ├── aws/                    AWS service clients (Bedrock, DynamoDB, S3, etc.)
│       ├── orchestration/          Campaign orchestration
│       ├── evaluation/             Metrics & correlation
│       ├── observability/          OpenTelemetry + X-Ray integration
│       ├── analysis/               Trace analysis & root cause
│       ├── factories/              Agent factory pattern
│       ├── application/            Business logic services
│       ├── api/                    REST API endpoints
│       └── config.py               Configuration management
│
├── 🎬 Demonstrations
│   └── demo/
│       ├── agenteval_demo_mock.py  Mock demo (no AWS, < 1 min)
│       ├── agenteval_live_demo.py  Live AWS demo (5 min, ~$0.10)
│       └── README.md               Demo documentation
│
├── 🛠️ Scripts
│   └── scripts/
│       ├── setup-live-demo.sh      AWS infrastructure setup
│       ├── teardown-live-demo.sh   Resource cleanup
│       ├── check-aws-services.sh   Service verification
│       └── run-live-demo.sh        Automated workflow
│
├── 🧪 Tests
│   └── tests/
│       ├── unit/                   Unit tests
│       ├── integration/            Integration tests
│       └── conftest.py             Pytest configuration
│
├── 📚 Hackathon Submission Documents
│   └── req-docs/
│       ├── AGENTS.md               ★ Master development reference
│       ├── BRD_AgentEval.md        Business requirements
│       ├── PRD_AgentEval.md        Product requirements
│       ├── TAD_Technical_Architecture.md  Technical design
│       ├── COMPLIANCE_CHECKLIST.md Submission requirements
│       ├── TEAM_INFO.md            Team information
│       ├── JUDGE_ACCESS.md         Judge access instructions
│       ├── TEST_DEMO_PLAYBOOK.md   Testing playbook
│       ├── CHANGE_LOG.md           Change history
│       ├── SUBMISSION_FREEZE.md    Submission freeze notice
│       └── ASSET_LICENSES.md       Asset licensing info
│
├── 🏗️ Infrastructure & Configuration
│   ├── infrastructure/             CloudFormation templates & IAM policies
│   ├── architecture/               Architecture diagrams (Mermaid)
│   ├── personas/                   Persona library (YAML)
│   ├── attacks/                    Red team attack library (YAML)
│   ├── metrics/                    Evaluation metrics library (YAML)
│   └── docs/                       Deployment documentation
│
├── 📝 Configuration Files
│   ├── pyproject.toml              Python project configuration
│   ├── pytest.ini                  Pytest configuration
│   ├── .env.example                Environment variables template
│   ├── .gitignore                  Git ignore rules
│   └── .python-version             Python version specification
│
├── 💡 Examples
│   └── examples/
│       └── demo_chatbot/           Example target system for testing
│
└── 📦 Archive (Not for Review)
    └── .archive/
        ├── development-docs/       Internal development documents
        ├── htmlcov/                Test coverage reports
        └── resources/              Internal audit & progress tracking

```

______________________________________________________________________

## 🎯 Quick Navigation for Judges

### **For Quick Evaluation (< 5 minutes)**

1. **📖 Read**: `SUBMISSION_GUIDE.md` - Complete navigation guide
1. **📖 Read**: `README.md` - Project overview
1. **🚀 Run**: `python demo/agenteval_demo_mock.py` - Mock demo (no AWS)

### **For Thorough Evaluation (15 minutes)**

1. **📖 Read**: `SUBMISSION_GUIDE.md` + `README.md`
1. **📖 Review**: `req-docs/AGENTS.md` - Master technical reference
1. **🚀 Run**: Mock demo + review code in `src/agenteval/`
1. **🔍 Check**: Test coverage with `pytest tests/ --cov`

### **For Complete Validation (30 minutes)**

1. **📖 Read**: All documentation above
1. **🚀 Run**: `scripts/run-live-demo.sh --auto-teardown` - Full AWS demo
1. **🔍 Review**: Architecture, code quality, test coverage
1. **✅ Verify**: All hackathon requirements met

______________________________________________________________________

## 📊 Key Statistics

| Metric                  | Value                                                     |
| ----------------------- | --------------------------------------------------------- |
| **Source Files**        | 50+ Python files                                          |
| **Lines of Code**       | ~8,000+                                                   |
| **Test Coverage**       | 93%                                                       |
| **Documentation Files** | 20+                                                       |
| **AWS Services**        | 6 (Bedrock, DynamoDB, S3, EventBridge, X-Ray, CloudWatch) |
| **Agent Types**         | 3 (Persona, Red Team, Judge)                              |
| **Personas**            | 10 pre-configured                                         |
| **Attack Patterns**     | 50+                                                       |
| **Evaluation Metrics**  | 13                                                        |

______________________________________________________________________

## 🔧 Technology Stack

### **Core Technologies**

- **Python 3.11+** - Primary language
- **FastAPI** - REST API framework
- **Pydantic** - Data validation & settings
- **Pytest** - Testing framework

### **AWS Services**

- **Amazon Bedrock** - Claude Haiku 4.5, Nova Pro
- **DynamoDB** - State management (4 tables)
- **Amazon S3** - Results storage (2 buckets)
- **EventBridge** - Event-driven coordination
- **AWS X-Ray** - Distributed tracing
- **CloudWatch** - Logging & monitoring

### **Observability**

- **OpenTelemetry** - Distributed tracing SDK
- **AWS X-Ray** - Trace backend
- **Structured Logging** - JSON logs

### **Development Tools**

- **uv** - Fast Python package manager
- **pytest** - Testing with coverage
- **black** - Code formatting
- **mypy** - Type checking

______________________________________________________________________

## 🧹 Cleanup & Organization Changes

### **Archived (Moved to .archive/)**

Development artifacts not needed for submission:

- ✅ `DI_ARCHITECTURE_PROPOSAL.md` - DI design document
- ✅ `DI_MIGRATION_EXAMPLES.md` - Migration examples
- ✅ `IMPLEMENTATION_COMPLETE.md` - Implementation progress
- ✅ `REFACTORING_PROGRESS.md` - Refactoring progress
- ✅ `AUDIT_REPORT.md` - Internal audit report
- ✅ `LIVE_DEMO_SUMMARY.md` - Old demo summary
- ✅ `resources/` - Internal progress tracking
- ✅ `htmlcov/` - Test coverage HTML reports
- ✅ `envs/` - Environment-specific configs

### **Removed (Final Cleanup)**

Redundant and temporary files:

- ✅ `ALL_FIXES_COMPLETE.md` - Redundant verification doc
- ✅ `FINAL_DEMO_RESULTS.md` - Redundant verification doc
- ✅ `FINAL_VALIDATION_REPORT.md` - Redundant verification doc
- ✅ `FIXES_SUMMARY.md` - Redundant verification doc
- ✅ `LIVE_DEMO_RESULTS.md` - Redundant verification doc
- ✅ `VERIFICATION_COMPLETE.md` - Redundant verification doc
- ✅ `compliance_tmp/` - Temporary hackathon rules cache
- ✅ `TEST_COVERAGE_PROGRESS.md` - Outdated progress tracking
- ✅ `src/demo/` - Duplicate demo directory
- ✅ `scripts/deploy.sh` - Replaced by setup-live-demo.sh
- ✅ `scripts/pull-live-reports.py` - Replaced by pull-demo-results.sh
- ✅ `.coverage` - Pytest coverage database
- ✅ `__pycache__/` - Python cache directories
- ✅ `.DS_Store` - Mac OS metadata files

### **Organized**

- ✅ Policy files moved to `infrastructure/`
- ✅ Development docs archived
- ✅ `.gitignore` created for cleaner repo
- ✅ Single verification document: `CLAUDE_HAIKU_VERIFICATION.md`

### **Updated for Consistency**

- ✅ All model references updated to **Claude Haiku 4.5**
- ✅ All documentation aligned with latest architecture
- ✅ README.md updated with submission guide link
- ✅ Demo scripts updated with correct DI container calls
- ✅ Consolidated verification into single authoritative document

______________________________________________________________________

## 📖 Documentation Index

### **Essential Documents (Read First)**

| Document                       | Purpose                                 | Time   |
| ------------------------------ | --------------------------------------- | ------ |
| `SUBMISSION_GUIDE.md`          | Complete navigation & evaluation guide  | 5 min  |
| `README.md`                    | Project overview, features, quick start | 5 min  |
| `LIVE_DEMO_GUIDE.md`           | Detailed demo instructions              | 10 min |
| `CLAUDE_HAIKU_VERIFICATION.md` | Complete verification & testing results | 5 min  |

### **Technical Documentation**

| Document                                 | Content                      | Audience   |
| ---------------------------------------- | ---------------------------- | ---------- |
| `req-docs/AGENTS.md`                     | Master development reference | Engineers  |
| `req-docs/TAD_Technical_Architecture.md` | Technical design             | Architects |
| `req-docs/BRD_AgentEval.md`              | Business requirements        | Business   |
| `req-docs/PRD_AgentEval.md`              | Product requirements         | Product    |

### **Submission Documents**

| Document                           | Purpose                              |
| ---------------------------------- | ------------------------------------ |
| `req-docs/COMPLIANCE_CHECKLIST.md` | Submission requirements verification |
| `req-docs/TEAM_INFO.md`            | Team member information              |
| `req-docs/JUDGE_ACCESS.md`         | Judge access credentials             |
| `req-docs/TEST_DEMO_PLAYBOOK.md`   | Testing procedures                   |
| `req-docs/CHANGE_LOG.md`           | Change history                       |
| `req-docs/SUBMISSION_FREEZE.md`    | Submission freeze notice             |

### **Additional Resources**

| Document                  | Content                           |
| ------------------------- | --------------------------------- |
| `QUICK_START_JUDGES.md`   | Quick judge evaluation guide      |
| `docs/DEPLOYMENT.md`      | Deployment guide                  |
| `demo/README.md`          | Demo comparison & troubleshooting |
| `architecture/diagram.md` | Mermaid architecture diagram      |
| `LICENSE`                 | MIT License text                  |
| `NOTICE.md`               | Third-party notices               |
| `ATTRIBUTIONS.md`         | Dependency licenses               |

______________________________________________________________________

## ✅ Verification Checklist

### **Documentation**

- ✅ README.md updated with submission notice
- ✅ SUBMISSION_GUIDE.md created
- ✅ All model references updated to Haiku 4.5
- ✅ All AWS service references accurate
- ✅ Architecture diagrams up to date

### **Code**

- ✅ All agents functional (Persona, Red Team, Judge)
- ✅ AWS clients working (Bedrock, DynamoDB, S3, etc.)
- ✅ Configuration aligned across all files
- ✅ Demo scripts updated with correct DI calls

### **Scripts**

- ✅ setup-live-demo.sh using Haiku 4.5
- ✅ teardown-live-demo.sh cleaning all resources
- ✅ check-aws-services.sh verifying Haiku 4.5
- ✅ run-live-demo.sh automated workflow

### **Testing**

- ✅ Mock demo working (no AWS)
- ✅ Live demo working (with AWS)
- ✅ Unit tests passing
- ✅ Integration tests passing
- ✅ Test coverage >90%

### **Organization**

- ✅ Development docs archived
- ✅ Root directory clean
- ✅ .gitignore configured
- ✅ Files properly categorized

______________________________________________________________________

## 🚀 Quick Start Commands

### **For Judges**

```bash
# 1. Quick mock demo (< 1 minute, no AWS)
python demo/agenteval_demo_mock.py

# 2. Run tests with coverage
pytest tests/ -v --cov=agenteval

# 3. Full live demo (requires AWS, ~5 minutes, ~$0.10)
scripts/run-live-demo.sh --auto-teardown
```

### **For Developers**

```bash
# Setup development environment
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Setup AWS infrastructure
scripts/setup-live-demo.sh --region us-east-1

# Run live demo
python demo/agenteval_live_demo.py

# Cleanup
scripts/teardown-live-demo.sh --force
```

______________________________________________________________________

## 📞 Support

For any questions or issues:

1. **Documentation**: Check `SUBMISSION_GUIDE.md` and `LIVE_DEMO_GUIDE.md`
1. **Troubleshooting**: See `demo/README.md`
1. **Team Info**: See `req-docs/TEAM_INFO.md`
1. **Technical Details**: See `req-docs/AGENTS.md`

______________________________________________________________________

## 🎯 Submission Status

**Status**: ✅ **READY FOR SUBMISSION**

All requirements met:

- ✅ Working multi-agent system with 3 agent types
- ✅ AWS Bedrock integration (Claude Haiku 4.5, Nova Pro)
- ✅ 6 AWS services integrated
- ✅ Comprehensive documentation
- ✅ Working demos (mock & live)
- ✅ Test coverage >90%
- ✅ Clean repository organization
- ✅ All files aligned and consistent

______________________________________________________________________

**Last Verified**: October 2025 **Repository**: aws-agents **Team**: AgentEval Team **Hackathon**:
AWS AI Agent Global Hackathon 2025
