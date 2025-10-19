# Changelog

All notable changes to the AgentEval project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

______________________________________________________________________

## \[Unreleased\]

### Documentation Consolidation (October 19, 2025)

Major documentation consolidation effort to reduce redundancy and improve maintainability.

#### Added

- **META_RESPONSE_FIX.md** - Comprehensive consolidation of 8 meta-response hallucination fix
  documents
- **PROJECT_STATUS.md** - Consolidated project status report combining 4 status/summary documents
- **CHANGELOG.md** - This file, tracking all project changes going forward

#### Changed

- Updated DOCUMENTATION_INDEX.md to reflect new consolidated structure
- Improved cross-references between documentation files

#### Removed/Archived

- Moved 8 meta-response fix documents to conceptual archive (content preserved in
  META_RESPONSE_FIX.md):

  - FIXES_APPLIED.md
  - FIX_VALIDATION_RESULTS.md
  - FINAL_VALIDATION_REPORT.md
  - ERROR_ANALYSIS.md
  - HALLUCINATION_REPORT.md
  - DASHBOARD_DIAGNOSIS.md
  - VALIDATION_SUMMARY.md
  - FINAL_COMPREHENSIVE_DEMO_REPORT.md (kept for reference, consolidated into META_RESPONSE_FIX.md)

- Moved 4 status/summary documents to conceptual archive (content preserved in PROJECT_STATUS.md):

  - FINAL_STATUS.md
  - FINAL_SUMMARY.md
  - SUBMISSION_SUMMARY.md
  - ISSUES_FOUND_AND_FIXES.md

______________________________________________________________________

## \[2.0.0\] - 2025-10-19

### Meta-Response Hallucination Fix - Production Release

Critical bug fix for persona agent meta-response hallucinations with comprehensive validation.

#### Fixed

- **Critical**: Meta-response hallucination in Turn 2+ persona messages
  - Persona agents were exposing internal state ("Current State: ...", "Frustration Level: ...")
    instead of generating natural dialogue
  - Implemented three-layer defense system: early validation, sentence filtering, prompt
    strengthening
  - Achieved 100% prevention rate across 22 campaigns (45+ detections, 0 in storage)
  - Added comprehensive unit tests (28/28 passing, coverage improved from 13% → 58%)

#### Added

- **Three-Layer Defense System**:

  - Layer 1: Early validation in `_sanitize_user_message()` with pattern matching (\< 1ms overhead)
  - Layer 2: Expanded meta-marker filtering (31 patterns) in sentence processing
  - Layer 3: Strengthened prompt with explicit instructions not to echo context

- **Static Validation Method**: `validate_user_message()` for external validation use

- **Comprehensive Test Suite**: 5 new tests in `TestMetaResponseValidation` class

  - test_validate_user_message_valid
  - test_validate_user_message_meta_response
  - test_validate_user_message_case_insensitive
  - test_sanitize_rejects_meta_response
  - test_generate_message_handles_meta_response_from_llm

#### Changed

- Modified `src/agenteval/agents/persona_agent.py` (+50 lines)
- Modified `tests/unit/test_persona_agent.py` (+93 lines)
- Updated ARCHITECTURE_UPDATE.md with meta-response prevention details

#### Validated

- ✅ 22 Total Campaigns executed (20 persona + 2 red team)
- ✅ 45+ Meta-response detections - 100% prevention rate
- ✅ ZERO storage contamination - perfect data integrity
- ✅ 100% campaign success rate
- ✅ Multiple demo runs (3 comprehensive executions, ~52 minutes total runtime)
- ✅ Storage integrity verification (grep confirmed 0 matches)

______________________________________________________________________

## \[1.3.0\] - 2025-10-19

### Auto-Reporting Pipeline Integration

Complete integration of 3-phase automatic reporting pipeline into core campaign execution.

#### Added

- **Phase 1: Auto-Pull Results**

  - Automatically downloads JSON data from DynamoDB and S3 after campaign completion
  - Saves to `outputs/campaign-results/<campaign_id>/`
  - Configuration: `auto_pull_results_to_local=true` (default enabled)
  - Non-fatal errors (campaign succeeds regardless of pull failure)

- **Phase 2: HTML Dashboard Generation**

  - Automatic creation of interactive dashboards with Chart.js
  - Generates: dashboard.html, campaign\_\*.html, summary.html
  - Saves to `demo/evidence/reports/`
  - Configuration: `auto_generate_dashboard=true` (default enabled)

- **Phase 3: Evidence Report Generation**

  - Automatic markdown evidence dashboard creation
  - Generates: dashboard.md, live-demo-latest.md
  - Saves to `demo/evidence/`
  - Configuration: `auto_generate_evidence_report=true` (default enabled)

#### Changed

- Modified `src/agenteval/config.py` - Added 6 new configuration fields for auto-reporting
- Modified `src/agenteval/orchestration/campaign.py` - Integrated complete 3-phase pipeline
- Updated WORKFLOWS.md with complete auto-reporting workflow documentation
- Updated INTEGRATED_COMPONENTS.md with integration architecture details

#### Benefits

- Zero manual steps required for result retrieval
- Multiple formats (JSON, HTML, Markdown) available immediately
- Seamless user experience
- Flexible (each phase can be individually disabled)

______________________________________________________________________

## \[1.2.0\] - 2025-10-19

### Critical Bug Fixes

Multiple critical bugs discovered and fixed during comprehensive integration testing.

#### Fixed

- **Bug 1**: Dashboard Only Showing 1 Campaign

  - File: `src/agenteval/reporting/dashboard.py:139`
  - Issue: Indentation bug with `campaigns.append()` outside for loop
  - Impact: All campaigns now appear in reports

- **Bug 2**: Attack Category "obfuscation" Invalid

  - Files: `demo/agenteval_live_demo.py`, `demo/comprehensive_demo_config.yaml`,
    `SCALING_CAPABILITIES.md`
  - Issue: Used "obfuscation" instead of correct enum value "encoding"
  - Impact: Red team campaigns now run with all 4 attack categories (injection, jailbreak,
    social_engineering, encoding)

- **Bug 3**: Only 1 Persona Running (Should Be 10)

  - File: `demo/agenteval_live_demo.py:336-402`
  - Issue: No loop to iterate through personas list
  - Impact: All 10 personas now execute in full mode

- **Bug 4**: HTML Dashboard DynamoDB Scan Failing

  - Files: `src/agenteval/aws/dynamodb.py:712-758`,
    `src/agenteval/application/results_service.py:318`
  - Issue: DynamoDBClient missing `scan_table()` method
  - Added: New method with pagination support
  - Impact: HTML dashboards now display all campaign data from DynamoDB

#### Verified

- All campaigns appear in both markdown and HTML dashboards
- All 10 personas run in full mode
- Red team uses all 4 attack categories
- DynamoDB data correctly retrieved and displayed

______________________________________________________________________

## \[1.1.0\] - 2025-10-18

### Comprehensive Testing Library

Expanded testing capabilities to support all available test cases.

#### Added

- **10 Personas**: All personas from library now available

  1. frustrated_customer
  1. technical_expert
  1. elderly_user
  1. adversarial_user
  1. impatient_executive
  1. curious_student
  1. skeptical_journalist
  1. non_native_speaker
  1. overwhelmed_parent
  1. security_conscious_user

- **20 Attacks** across 4 categories:

  - Injection (5 attacks)
  - Jailbreak (5 attacks)
  - Social Engineering (5 attacks)
  - Encoding (5 attacks)

- **13 Metrics**:

  - Quality metrics (7): accuracy, relevance, completeness, clarity, coherence, routing_accuracy,
    helpfulness
  - Safety metrics (5): toxicity, bias, harmful_content, privacy_leak, session_handling
  - Performance metrics (1): latency

- **Configuration System**: Created `demo/comprehensive_demo_config.yaml` with granular control

  - Individual enable/disable for each persona, attack, and metric
  - Per-item configuration (turns, priority, severity)
  - Execution settings (timeouts, parallel campaigns)

______________________________________________________________________

## \[1.0.0\] - 2025-10-15

### Initial Production Release

First production-ready release of AgentEval AI agent testing platform.

#### Added

- **Core Features**:

  - Campaign orchestration system
  - Persona agent framework for behavioral testing
  - Red team agent framework for security assessment
  - Judge agent framework for evaluation
  - Multi-turn conversation simulation
  - Real-time evaluation with 11 metrics

- **AWS Integration**:

  - Amazon Bedrock (LLM inference)
  - DynamoDB (state persistence)
  - S3 (results/reports storage)
  - EventBridge (event-driven workflows)
  - X-Ray (distributed tracing)

- **Observability**:

  - OpenTelemetry instrumentation
  - Structured logging
  - Event publishing for monitoring
  - Trace correlation

- **API Layer**:

  - FastAPI-based REST API
  - Admin dashboard routes
  - Campaign management endpoints
  - Authentication and rate limiting

- **Reporting & Analytics**:

  - Real-time report generation
  - Root cause analysis
  - Correlation analytics
  - Evidence dashboards (HTML and Markdown)

#### Validated

- 625 passing unit tests
- 68% code coverage
- Multiple successful live demos
- AWS integration validated end-to-end

______________________________________________________________________

## Documentation Structure Changes

### Current Structure (After Consolidation)

**Root Documentation** (15 files, reduced from 27):

- README.md - Main project overview
- META_RESPONSE_FIX.md - Consolidated fix documentation (NEW)
- PROJECT_STATUS.md - Consolidated status report (NEW)
- CHANGELOG.md - This file (NEW)
- SYSTEM_ARCHITECTURE.md - Complete architecture
- WORKFLOWS.md - Development workflows
- LIVE_DEMO_GUIDE.md - Demo instructions
- QUICK_START_JUDGES.md - Quick evaluation guide
- SUBMISSION_GUIDE.md - Hackathon submission
- REPOSITORY_ORGANIZATION.md - Project structure
- INTEGRATED_COMPONENTS.md - Component integration
- SCALING_CAPABILITIES.md - Scaling guide
- DOCUMENTATION_INDEX.md - Documentation navigation
- NOTICE.md - Legal notices
- ATTRIBUTIONS.md - Third-party attributions

**Subdirectories** (Preserved):

- `architecture/` - Architecture diagrams and future plans
- `docs/` - Deployment and operational guides
- `examples/` - Demo chatbot example
- `req-docs/` - Requirements and planning documents
- `.archive/` - Archived historical documentation

**Generated Outputs** (Auto-generated):

- `demo/evidence/` - Evidence dashboards and reports
- `outputs/campaign-results/` - Campaign data and results

______________________________________________________________________

## Migration Guide

### For Users of Archived Documents

If you previously referenced any of the following documents, use the new consolidated versions:

**Meta-Response Fix Documentation** → Use `META_RESPONSE_FIX.md`

- Old: FIXES_APPLIED.md, FIX_VALIDATION_RESULTS.md, FINAL_VALIDATION_REPORT.md, ERROR_ANALYSIS.md,
  HALLUCINATION_REPORT.md, DASHBOARD_DIAGNOSIS.md, VALIDATION_SUMMARY.md
- New: META_RESPONSE_FIX.md (comprehensive consolidation)
- Content: All unique information preserved

**Project Status** → Use `PROJECT_STATUS.md`

- Old: FINAL_STATUS.md, FINAL_SUMMARY.md, SUBMISSION_SUMMARY.md, ISSUES_FOUND_AND_FIXES.md
- New: PROJECT_STATUS.md (comprehensive consolidation)
- Content: All achievements, fixes, and status information preserved

**Change Tracking** → Use `CHANGELOG.md`

- Old: Scattered across multiple status documents
- New: CHANGELOG.md (this file)
- Content: Chronological change history with semantic versioning

______________________________________________________________________

## Future Releases

### Planned for v2.1.0

- [ ] Increase test coverage to 80% (currently 68%)
- [ ] Fix resource leaks (unclosed asyncio sessions)
- [ ] Architecture cleanup (move demo code out of src/)
- [ ] Enhanced monitoring dashboard with meta-response detection metrics

### Planned for v2.2.0

- [ ] AWS inference profile setup automation
- [ ] Improved fallback message quality (contextual instead of generic)
- [ ] Integration tests for complete campaign workflows
- [ ] Parallel campaign execution support

### Planned for v3.0.0

- [ ] ML-based meta-response detection
- [ ] Advanced correlation analytics
- [ ] Enhanced reporting visualizations
- [ ] Load testing and performance optimization

______________________________________________________________________

## Contributing

When making changes, please:

1. Update the relevant section in this CHANGELOG.md
1. Follow semantic versioning guidelines
1. Document breaking changes clearly
1. Update related documentation files
1. Add tests for new features
1. Run full test suite before committing

______________________________________________________________________

## Links

- **Documentation Index**: DOCUMENTATION_INDEX.md
- **System Architecture**: SYSTEM_ARCHITECTURE.md
- **Meta-Response Fix**: META_RESPONSE_FIX.md
- **Project Status**: PROJECT_STATUS.md
- **Workflows**: WORKFLOWS.md

______________________________________________________________________

**Maintained By**: AgentEval Development Team **Last Updated**: October 19, 2025 **Version**: 2.0.0
