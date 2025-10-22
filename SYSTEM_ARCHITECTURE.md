# AgentEval System Architecture

**Last Updated**: October 19, 2025 **Version**: 2.0.0 (includes Meta-Response Prevention Layer)
**Status**: ✅ Production Ready

______________________________________________________________________

## Table of Contents

1. [Overview](#overview)
1. [System Components](#system-components)
1. [Architecture Diagrams](#architecture-diagrams)
1. [Data Flow](#data-flow)
1. [Agent Architecture](#agent-architecture)
1. [Meta-Response Prevention Layer](#meta-response-prevention-layer)
1. [AWS Integration](#aws-integration)
1. [Observability & Tracing](#observability--tracing)
1. [Security Considerations](#security-considerations)

______________________________________________________________________

## Overview

AgentEval is a multi-agent AI evaluation platform built on AWS Bedrock with comprehensive
trace-based root cause analysis. The system features three autonomous agent types (Persona, Red
Team, Judge) that work together to evaluate GenAI applications.

### Key Architectural Principles

1. **Agent Autonomy** - Each agent operates independently with its own state
1. **Event-Driven** - EventBridge-based event propagation
1. **Cloud-Native** - Built for AWS with Bedrock, DynamoDB, S3, X-Ray
1. **Observability-First** - OpenTelemetry tracing throughout
1. **Hot-Reloadable** - YAML-based configuration for agents without code changes

______________________________________________________________________

## System Components

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        AgentEval Platform                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Persona    │  │  Red Team    │  │    Judge     │          │
│  │    Agent     │  │    Agent     │  │    Agent     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                  │                  │                  │
│         └──────────────────┴──────────────────┘                 │
│                            │                                     │
│                 ┌──────────┴──────────┐                         │
│                 │                     │                          │
│         ┌───────▼──────┐      ┌──────▼────────┐                │
│         │   Campaign   │      │     Memory    │                │
│         │ Orchestrator │      │    System     │                │
│         └───────┬──────┘      └───────────────┘                │
│                 │                                                │
│     ┌───────────┼───────────┐                                   │
│     │           │           │                                   │
│ ┌───▼───┐  ┌───▼────┐  ┌───▼────┐                              │
│ │  AWS  │  │  AWS   │  │  AWS   │                              │
│ │Bedrock│  │DynamoDB│  │   S3   │                              │
│ └───────┘  └────────┘  └────────┘                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Descriptions

| Component                    | Purpose                                                  | Technology                     |
| ---------------------------- | -------------------------------------------------------- | ------------------------------ |
| **Persona Agent**            | Simulates realistic user behaviors with memory and state | Python, AWS Bedrock            |
| **Red Team Agent**           | Automated security testing with attack patterns          | Python, AWS Bedrock            |
| **Judge Agent**              | Evaluates responses across 11+ metrics                   | Python, AWS Bedrock (Nova Pro) |
| **Campaign Orchestrator**    | Manages campaign lifecycle and turn execution            | Python, asyncio                |
| **Memory System**            | Multi-level memory (preferences, facts, summaries)       | Python, in-memory              |
| **Meta-Response Prevention** | Validates and sanitizes agent outputs                    | Python, pattern matching       |

______________________________________________________________________

## Architecture Diagrams

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           User / Demo Runner                             │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         Campaign Orchestrator                            │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │  Campaign State Machine                                         │    │
│  │  - Created → Running → Evaluating → Completed                   │    │
│  └────────────────────────────────────────────────────────────────┘    │
└──────┬──────────────┬──────────────┬──────────────┬────────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Persona   │ │  Red Team   │ │    Judge    │ │   Trace     │
│    Agent    │ │    Agent    │ │    Agent    │ │  Analyzer   │
│  Factory    │ │  Factory    │ │  Factory    │ │             │
└─────┬───────┘ └─────┬───────┘ └─────┬───────┘ └─────┬───────┘
      │               │               │               │
      ▼               ▼               ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                        AWS Bedrock (LLM Inference)                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │Claude Haiku │  │Claude Haiku │  │  Nova Pro   │              │
│  │  (Persona)  │  │ (Red Team)  │  │   (Judge)   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│         ↓ Fallback          ↓ Fallback                           │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │Titan Lite   │  │Titan Lite   │                               │
│  └─────────────┘  └─────────────┘                               │
└──────────────────────────────────────────────────────────────────┘
      │               │               │               │
      ▼               ▼               ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     AWS Storage & Events                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  DynamoDB   │  │     S3      │  │ EventBridge │              │
│  │  (State)    │  │  (Results)  │  │   (Events)  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└──────────────────────────────────────────────────────────────────┘
      │               │               │
      ▼               ▼               ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Observability & Monitoring                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   X-Ray     │  │ CloudWatch  │  │OpenTelemetry│              │
│  │  (Tracing)  │  │   (Logs)    │  │  (Traces)   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

### Campaign Execution Flow

```
┌────────────┐
│   Start    │
│  Campaign  │
└──────┬─────┘
       │
       ▼
┌────────────────────┐
│  Create Campaign   │
│  (DynamoDB record) │
└──────┬─────────────┘
       │
       ▼
┌────────────────────┐
│ Initialize Agents  │
│ - Persona Factory  │
│ - Judge Factory    │
└──────┬─────────────┘
       │
       ▼
┌────────────────────┐
│   Execute Turn 1   │◄──────┐
└──────┬─────────────┘       │
       │                     │
       ▼                     │
┌────────────────────┐       │
│ Persona generates  │       │
│  user message      │       │
│  (with meta-       │       │
│   response check)  │       │
└──────┬─────────────┘       │
       │                     │
       ▼                     │
┌────────────────────┐       │
│  Send to target    │       │
│     system         │       │
└──────┬─────────────┘       │
       │                     │
       ▼                     │
┌────────────────────┐       │
│ Judge evaluates    │       │
│  (11 metrics)      │       │
└──────┬─────────────┘       │
       │                     │
       ▼                     │
┌────────────────────┐       │
│  Store results     │       │
│  (DynamoDB + S3)   │       │
└──────┬─────────────┘       │
       │                     │
       ▼                     │
┌────────────────────┐       │
│ Publish events     │       │
│  (EventBridge)     │       │
└──────┬─────────────┘       │
       │                     │
       ▼                     │
       No ◄─ More turns? ────┘
       │ Yes
       ▼
┌────────────────────┐
│ Generate reports   │
│  (S3)              │
└──────┬─────────────┘
       │
       ▼
┌────────────────────┐
│   Pull results     │
│  (to local)        │
└──────┬─────────────┘
       │
       ▼
┌────────────────────┐
│  Campaign complete │
└────────────────────┘
```

______________________________________________________________________

## Data Flow

### Turn Execution Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                            Turn N                                │
└─────────────────────────────────────────────────────────────────┘

1. Persona Agent
   ┌────────────────────┐
   │  Get full memory   │
   │     context        │
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │ Generate message   │
   │  via LLM           │
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐      ┌──────────────────────┐
   │ Meta-response      │──Yes─►│ Use fallback message │
   │   detected?        │      └──────────┬───────────┘
   └─────────┬──────────┘                 │
             │ No                          │
             └─────────────────────────────┘
             │
             ▼
   ┌────────────────────┐
   │ Sanitize message   │
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  Store to memory   │
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │ Send to target     │
   │     system         │
   └─────────┬──────────┘
             │
             ▼

2. Target System Response
   ┌────────────────────┐
   │ Receive response   │
   └─────────┬──────────┘
             │
             ▼

3. Judge Agent
   ┌────────────────────┐
   │  Evaluate across   │
   │   11 metrics       │
   └─────────┬──────────┘
             │
   ┌─────────┴──────────┐
   │                    │
   ▼                    ▼
┌──────────┐      ┌──────────┐
│ Quality  │      │  Safety  │
│ Metrics  │      │ Metrics  │
│ (5)      │      │ (6)      │
└─────┬────┘      └─────┬────┘
      │                 │
      └────────┬────────┘
               │
               ▼
   ┌────────────────────┐
   │  Store evaluation  │
   │   (DynamoDB)       │
   └─────────┬──────────┘
             │
             ▼

4. Event Publishing
   ┌────────────────────┐
   │  TurnCompleted     │
   │  event to          │
   │  EventBridge       │
   └─────────┬──────────┘
             │
             ▼

5. Tracing
   ┌────────────────────┐
   │ Emit trace spans   │
   │  to X-Ray          │
   └────────────────────┘
```

______________________________________________________________________

## Agent Architecture

### Persona Agent Internal Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Persona Agent                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                   Persona Library                     │       │
│  │  (YAML) - 10 personas with goals, traits, emotions   │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Memory System (3 Levels)                 │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐  │       │
│  │  │ Preferences  │  │    Facts     │  │ Summaries │  │       │
│  │  └──────────────┘  └──────────────┘  └───────────┘  │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                 State Tracking                        │       │
│  │  - frustration_level (0-10)                          │       │
│  │  - patience_level (0-10)                             │       │
│  │  - goal_progress (0.0-1.0)                           │       │
│  │  - interaction_count                                 │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │            Message Generation Pipeline                │       │
│  │                                                       │       │
│  │  1. Build context from memory                        │       │
│  │  2. Invoke LLM (Claude Haiku / Titan Lite)          │       │
│  │  3. ┌─────────────────────────────────────┐          │       │
│  │     │  Meta-Response Prevention Layer     │          │       │
│  │     │  ┌───────────────────────────────┐  │          │       │
│  │     │  │ Pattern matching validation   │  │          │       │
│  │     │  │ - "current state:"            │  │          │       │
│  │     │  │ - "frustration level:"        │  │          │       │
│  │     │  │ - "patience level:"           │  │          │       │
│  │     │  │ - "goal progress:"            │  │          │       │
│  │     │  └───────────────────────────────┘  │          │       │
│  │     │  If detected → Use fallback message │          │       │
│  │     └─────────────────────────────────────┘          │       │
│  │  4. Sanitize output                                  │       │
│  │  5. Store to memory                                  │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                 Natural User Message                  │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Red Team Agent Internal Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Red Team Agent                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │                  Attack Library                       │       │
│  │  (YAML) - 20 attacks across 4 categories             │       │
│  │  - Injection (SQL, Prompt, Command)                  │       │
│  │  - Jailbreak (System bypass, Role confusion)         │       │
│  │  - Social Engineering (Phishing, Authority)          │       │
│  │  - Encoding (Base64, Hex, Unicode)                   │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │            Knowledge Base (DynamoDB)                  │       │
│  │  - Successful attacks                                │       │
│  │  - Failed attacks                                    │       │
│  │  - System vulnerabilities                            │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           Evolutionary Attack Generation              │       │
│  │  1. Select attack pattern                            │       │
│  │  2. Mutate based on knowledge                        │       │
│  │  3. Invoke LLM for creative variants                 │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Success Evaluation                       │       │
│  │  - Regex pattern matching                            │       │
│  │  - HTTP status code analysis                         │       │
│  │  - LLM-based evaluation                              │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │           Update Knowledge Base                       │       │
│  │  (Store successful attacks for future use)           │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Judge Agent Internal Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          Judge Agent                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │              Evaluation Metrics (11)                  │       │
│  │                                                       │       │
│  │  Quality Metrics (5):                                │       │
│  │  ├─ accuracy                                          │       │
│  │  ├─ relevance                                         │       │
│  │  ├─ completeness                                      │       │
│  │  ├─ clarity                                           │       │
│  │  └─ coherence                                         │       │
│  │                                                       │       │
│  │  Safety Metrics (6):                                 │       │
│  │  ├─ toxicity                                          │       │
│  │  ├─ bias                                              │       │
│  │  ├─ harmful_content                                   │       │
│  │  ├─ privacy_leak                                      │       │
│  │  ├─ routing_accuracy                                  │       │
│  │  └─ session_handling                                  │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │            Per-Metric Evaluation                      │       │
│  │  For each metric:                                    │       │
│  │  1. Build evaluation prompt                          │       │
│  │  2. Invoke LLM (Nova Pro)                            │       │
│  │  3. Parse score (0.0-1.0)                            │       │
│  │  4. Extract reasoning                                │       │
│  │  5. Determine pass/fail (threshold: 0.7)             │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │             Aggregate Results                         │       │
│  │  - Overall score (average)                           │       │
│  │  - Pass/fail count                                   │       │
│  │  - Per-metric breakdown                              │       │
│  └────────────────────┬─────────────────────────────────┘       │
│                       │                                          │
│                       ▼                                          │
│  ┌──────────────────────────────────────────────────────┐       │
│  │             Store to DynamoDB                         │       │
│  │  (agenteval-evaluations table)                       │       │
│  └──────────────────────────────────────────────────────┘       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

______________________________________________________________________

## Meta-Response Prevention Layer

**Added**: October 19, 2025 **Status**: ✅ Production Validated (22 campaigns, 45+ detections, 0%
storage contamination)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│              Meta-Response Prevention Layer                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Layer 1: Early Validation (_sanitize_user_message)            │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Pattern Detection:                                 │         │
│  │  - "current state:"                                │         │
│  │  - "frustration level:"                            │         │
│  │  - "patience level:"                               │         │
│  │  - "goal progress:"                                │         │
│  │  - "interaction count:"                            │         │
│  │                                                    │         │
│  │  If detected:                                      │         │
│  │  → Log WARNING                                     │         │
│  │  → Return fallback message (persona goal)         │         │
│  └────────────────────┬───────────────────────────────┘         │
│                       │                                          │
│                       ▼                                          │
│  Layer 2: Sentence Filtering (meta_markers)                    │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Expanded marker tuple (31 patterns):              │         │
│  │  - Internal state keywords                         │         │
│  │  - Meta-commentary indicators                      │         │
│  │  - Role confusion markers                          │         │
│  │                                                    │         │
│  │  Filters out sentences containing markers          │         │
│  └────────────────────┬───────────────────────────────┘         │
│                       │                                          │
│                       ▼                                          │
│  Layer 3: Prompt Strengthening                                 │
│  ┌────────────────────────────────────────────────────┐         │
│  │  Explicit instructions to LLM:                     │         │
│  │  - "Do NOT repeat or echo context"                 │         │
│  │  - "Do NOT include state information"              │         │
│  │  - "Provide ONLY natural language message"         │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                  │
│  Performance:                                                   │
│  - Latency: < 1ms per message                                  │
│  - Memory: < 1KB (static pattern list)                         │
│  - Cost: $0 (no additional LLM calls)                          │
│  - Detection Rate: 100% (45+ detections, 0 false negatives)    │
│  - Prevention Rate: 100% (0 meta-responses in storage)         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Integration Points

1. **src/agenteval/agents/persona_agent.py**

   - Lines 208-223: Early validation in `_sanitize_user_message()`
   - Lines 305-314: Expanded `meta_markers` tuple
   - Lines 401-409: Strengthened user prompt
   - Lines 377-402: Static `validate_user_message()` method

1. **tests/unit/test_persona_agent.py**

   - Lines 402-494: `TestMetaResponseValidation` class
   - 5 comprehensive unit tests
   - 100% test pass rate

### Validation Results

See [FINAL_COMPREHENSIVE_DEMO_REPORT.md](FINAL_COMPREHENSIVE_DEMO_REPORT.md) for complete validation
details.

______________________________________________________________________

## AWS Integration

### DynamoDB Schema

**Table 1: agenteval-campaigns**

```json
{
  "campaign_id": "uuid",
  "campaign_type": "persona | red_team",
  "status": "created | running | evaluating | completed | failed",
  "config": {
    "persona_type": "frustrated_customer",
    "initial_goal": "I need help",
    "max_turns": 3
  },
  "stats": {
    "total_turns": 3,
    "completed_turns": 3,
    "failed_turns": 0,
    "avg_score": 0.75
  },
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

**Table 2: agenteval-turns**

```json
{
  "turn_id": "uuid",
  "campaign_id": "uuid",
  "turn_number": 1,
  "user_message": "I need help with my account",
  "system_response": "How can I assist you?",
  "trace_id": "w3c-trace-id",
  "metadata": {
    "frustration_level": 5,
    "patience_level": 8
  },
  "timestamp": "timestamp"
}
```

**Table 3: agenteval-evaluations**

```json
{
  "evaluation_id": "uuid",
  "turn_id": "uuid",
  "campaign_id": "uuid",
  "judge_id": "uuid",
  "metrics": {
    "accuracy": {"score": 0.8, "passed": true, "reasoning": "..."},
    "relevance": {"score": 0.9, "passed": true, "reasoning": "..."}
    // ... 11 total metrics
  },
  "overall_score": 0.82,
  "timestamp": "timestamp"
}
```

**Table 4: agenteval-attack-knowledge**

```json
{
  "knowledge_id": "uuid",
  "attack_category": "injection",
  "attack_pattern": "sql_injection_basic",
  "success": true,
  "target_response": "...",
  "learned_at": "timestamp"
}
```

### S3 Structure

```
agenteval-results-{account-id}/
└── campaigns/
    └── {campaign_id}/
        ├── results.json          # Campaign summary
        └── report-{timestamp}.json  # Generated report

agenteval-reports-{account-id}/
└── reports/
    └── {campaign_id}/
        └── demo-report-{timestamp}.json  # Auto-generated report
```

### EventBridge Events

**Event 1: CampaignCreated**

```json
{
  "source": "agenteval",
  "detail-type": "CampaignCreated",
  "detail": {
    "campaign_id": "uuid",
    "campaign_type": "persona",
    "timestamp": "2025-10-19T12:00:00Z"
  }
}
```

**Event 2: TurnCompleted**

```json
{
  "source": "agenteval",
  "detail-type": "TurnCompleted",
  "detail": {
    "campaign_id": "uuid",
    "turn_id": "uuid",
    "turn_number": 1,
    "metrics_evaluated": 11,
    "timestamp": "2025-10-19T12:01:00Z"
  }
}
```

**Event 3: CampaignCompleted**

```json
{
  "source": "agenteval",
  "detail-type": "CampaignCompleted",
  "detail": {
    "campaign_id": "uuid",
    "total_turns": 3,
    "overall_score": 0.82,
    "duration_seconds": 120,
    "timestamp": "2025-10-19T12:05:00Z"
  }
}
```

______________________________________________________________________

## Observability & Tracing

### OpenTelemetry Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                    Trace Propagation Flow                        │
└─────────────────────────────────────────────────────────────────┘

Request Start
   │
   ▼
Generate W3C Trace Context
   │  traceparent: 00-{trace-id}-{span-id}-01
   │
   ▼
Campaign Orchestrator (Root Span)
   │
   ├─► Persona Agent Message Generation (Child Span)
   │   │
   │   ├─► LLM Invocation (Grandchild Span)
   │   │   └─ AWS Bedrock API call
   │   │
   │   └─► Meta-Response Validation (Grandchild Span)
   │
   ├─► Target System HTTP Call (Child Span)
   │   └─ Propagates traceparent header
   │
   ├─► Judge Agent Evaluation (Child Span)
   │   │
   │   ├─► Metric Evaluation (Grandchild Span) × 11
   │   │   └─ AWS Bedrock API call (Nova Pro)
   │   │
   │   └─► Result Aggregation (Grandchild Span)
   │
   ├─► DynamoDB Write (Child Span)
   │   └─ Store turn + evaluation
   │
   ├─► EventBridge Publish (Child Span)
   │   └─ Publish TurnCompleted event
   │
   └─► X-Ray Export (Child Span)
       └─ Send trace to AWS X-Ray
```

### Trace Attributes

**Span Attributes**:

- `campaign_id` - Campaign identifier
- `turn_number` - Turn sequence number
- `agent_type` - persona | red_team | judge
- `agent_id` - Agent instance identifier
- `model_id` - LLM model used
- `llm.output_tokens` - Token count
- `llm.stop_reason` - Completion reason
- `metric_type` - Judge metric being evaluated
- `metric_score` - Evaluation score
- `meta_response_detected` - Boolean flag (if applicable)

______________________________________________________________________

## Security Considerations

### Authentication & Authorization

- **AWS IAM** - Fine-grained permissions for Bedrock, DynamoDB, S3
- **Environment Variables** - Secrets stored in `.env` file (not committed)
- **Inference Profiles** - AWS managed access to model endpoints

### Data Protection

- **Encryption at Rest** - DynamoDB and S3 server-side encryption
- **Encryption in Transit** - TLS for all AWS API calls
- **No PII Storage** - Campaign data contains only test scenarios

### Meta-Response Prevention

- **Input Validation** - Pattern-based detection of internal state exposure
- **Output Sanitization** - Multiple layers of filtering
- **Fallback Mechanism** - Safe default messages if validation fails
- **Audit Logging** - All detections logged at WARNING level

______________________________________________________________________

## Performance Characteristics

### Latency

| Operation               | Typical Latency        | Notes                   |
| ----------------------- | ---------------------- | ----------------------- |
| **LLM Invocation**      | 2-5 seconds            | Titan Lite (fallback)   |
| **LLM Invocation**      | 1-3 seconds            | Claude Haiku (primary)  |
| **Judge Evaluation**    | 1-2 seconds per metric | Nova Pro                |
| **Meta-Response Check** | \< 1ms                 | Pattern matching        |
| **DynamoDB Write**      | 10-50ms                | Single-digit ms typical |
| **S3 Write**            | 50-200ms               | Depends on object size  |
| **EventBridge Publish** | 10-50ms                | Async operation         |
| **Complete Turn**       | 20-30 seconds          | End-to-end              |

### Throughput

- **Sequential Execution**: 1 campaign at a time (current)
- **Parallel Potential**: 100+ concurrent campaigns (with tuning)
- **Rate Limits**: AWS Bedrock API quotas (model-dependent)

### Resource Utilization

| Resource    | Usage                           |
| ----------- | ------------------------------- |
| **Memory**  | ~500MB per campaign             |
| **CPU**     | Low (I/O bound)                 |
| **Network** | ~1MB per turn (includes traces) |
| **Storage** | ~10KB per turn (DynamoDB + S3)  |

______________________________________________________________________

## Deployment Architecture

### Local Development

```
Developer Machine
├── Python 3.11+ runtime
├── Source code (src/)
├── Tests (tests/)
├── Configuration (.env)
└── AWS SDK (boto3, aioboto3)
      │
      └─► AWS Services (us-east-1)
          ├── Bedrock
          ├── DynamoDB
          ├── S3
          ├── EventBridge
          └── X-Ray
```

### Production Deployment (Potential)

```
AWS ECS/Fargate or Lambda
├── Container Image
│   ├── Python 3.11 runtime
│   ├── AgentEval code
│   └── Dependencies
├── IAM Role (least privilege)
├── VPC (optional)
└── CloudWatch Logs
      │
      └─► AWS Services
          ├── Bedrock (inference)
          ├── DynamoDB (state)
          ├── S3 (results)
          ├── EventBridge (events)
          ├── X-Ray (tracing)
          └── CloudWatch (metrics)
```

______________________________________________________________________

## Technology Stack

### Core Technologies

| Layer             | Technology             | Purpose                      |
| ----------------- | ---------------------- | ---------------------------- |
| **Language**      | Python 3.11+           | Primary development language |
| **Async Runtime** | asyncio, aioboto3      | Concurrent AWS operations    |
| **LLM Service**   | AWS Bedrock            | Model inference              |
| **Storage**       | DynamoDB, S3           | State and results            |
| **Events**        | EventBridge            | Event-driven architecture    |
| **Tracing**       | OpenTelemetry, X-Ray   | Distributed tracing          |
| **Testing**       | pytest, pytest-asyncio | Unit and integration tests   |
| **Configuration** | YAML, dotenv           | Hot-reloadable config        |
| **HTTP Client**   | httpx                  | Async HTTP with tracing      |

### AWS Services

| Service         | Purpose             | Usage                              |
| --------------- | ------------------- | ---------------------------------- |
| **Bedrock**     | LLM inference       | Claude Haiku, Titan Lite, Nova Pro |
| **DynamoDB**    | NoSQL database      | Campaign state, turns, evaluations |
| **S3**          | Object storage      | Results, reports, artifacts        |
| **EventBridge** | Event bus           | Campaign lifecycle events          |
| **X-Ray**       | Distributed tracing | Request correlation, performance   |
| **CloudWatch**  | Monitoring          | Logs, metrics (optional)           |
| **IAM**         | Authentication      | Service permissions                |

______________________________________________________________________

## Scaling Considerations

See [SCALING_CAPABILITIES.md](SCALING_CAPABILITIES.md) for detailed scaling analysis.

**Key Points**:

- Horizontal scaling via parallel campaign execution
- DynamoDB auto-scaling for variable load
- S3 unlimited storage capacity
- Bedrock API rate limits as primary constraint
- Cost optimization through efficient LLM usage

______________________________________________________________________

## Future Architecture Enhancements

1. **Parallel Campaign Execution** - Run multiple campaigns concurrently
1. **Model Quality Monitoring** - Automatic fallback detection and alerting
1. **Advanced Fallback Generation** - Context-aware fallback messages
1. **ML-Based Meta-Response Detection** - Train model to detect new patterns
1. **Real-Time Dashboard** - WebSocket-based live monitoring
1. **Multi-Region Support** - Deploy across multiple AWS regions
1. **Cost Optimization** - Intelligent model selection based on complexity
1. **Advanced Tracing** - Deeper correlation with business metrics

______________________________________________________________________

## References

- [FIXES_APPLIED.md](FIXES_APPLIED.md) - Meta-response prevention implementation
- [FINAL_COMPREHENSIVE_DEMO_REPORT.md](FINAL_COMPREHENSIVE_DEMO_REPORT.md) - Validation results
- [WORKFLOWS.md](WORKFLOWS.md) - Development workflows
- [SCALING_CAPABILITIES.md](SCALING_CAPABILITIES.md) - Scaling strategy

______________________________________________________________________

**Document Version**: 2.0.0 **Last Updated**: October 19, 2025 **Maintained By**: Issac Jose
Ignatius **Status**: ✅ Production Ready
