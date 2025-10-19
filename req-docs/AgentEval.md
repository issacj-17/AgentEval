# AgentEval – Doc-by-Doc Comparison & Improvement Plan

> Purpose: Compare the latest assistant-authored docs vs. your uploaded versions, highlight changes,
> validate Python-first implementation, and list improvements to finalize a Hackathon-ready
> **AGENTS.md** and supporting package.

______________________________________________________________________

## 🔧 Global Validation & Alignment

- **Primary language:** **Python 3.11** across API, agents, SDK, CI/CD, Docker base image.
- **AWS-first architecture:** Bedrock (Claude/Nova), X-Ray, DynamoDB, S3, EventBridge, ECS Fargate.
- **Hackathon fit:** Multi-agent (Persona, Red Team, Judge) + reasoning LLMs + autonomous
  orchestration + API/tool integrations.
- **Trace-first differentiator:** Root-cause correlation links evaluation scores to X-Ray spans.

**Cross-Doc Alignment Matrix (JTBD → Stories → System Reqs → Acceptance):**

| Jobs To Be Done                         | Representative User Story                                                | System Requirement                                                              | Acceptance Criteria                                                                                 |
| --------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Validate quality & safety before launch | As an AI engineer, I run an evaluation campaign to catch issues pre-prod | Multi-agent evaluation (Persona/Red Team/Judge) with 13 metrics                 | Overall score generated; low-score turns have trace-linked root causes + actionable recommendations |
| Prove security posture                  | As a security engineer, I run automated red-teaming                      | Attack library with curated categories (Injection, Jailbreak, Social, Encoding) | Successful attack detection accuracy ≥ 90%; severity tagged; evidence stored                        |
| Debug failures quickly                  | As an engineer, I inspect a failed turn                                  | Trace correlation into X-Ray spans with causal chain                            | Root cause identified with ≥90% confidence; fix suggestions + code snippets                         |
| Operate at scale                        | As DevOps, I run multiple campaigns concurrently                         | Async orchestration on ECS, DynamoDB state, S3 exports                          | 10 concurrent campaigns p95 latency \<200ms; completion \<5 min for 100 turns                       |

> This matrix is reflected in the PRD acceptance criteria and Agile DoD; gaps and corrections per
> document are listed below.

______________________________________________________________________

## 1) **AGENTS.md (Master Reference)**

### What Changed

- Promoted **Python-first** standards (3.11+, Async FastAPI, aioboto3) and added a one-glance
  **Developer Cheat Sheet** (model IDs, key endpoints, env vars, run commands).
- Added **Trace Correlation Quick-Start** (how to fetch a trace_id, where to look in X-Ray).
- Linked all sibling docs (BRD/PRD/TAD/Agile/Checklist) and inserted a **Doc Map**.

### How to Improve

- Add a **“Getting Unstuck” runbook**: common errors, trace signals, remediation steps.
- Include a compact **API & CLI table** for the top 8 commands with sample payloads.
- Add a **JTBD→Story→Req→AC grid** (now included above) directly into AGENTS.md.
- Insert **security & compliance footnotes** (PII handling, model safety prompts).

______________________________________________________________________

## 2) **BRD_AgentEval.md**

### What Changed

- Tightened link from **business KPIs** to PRD technical metrics (evaluation speed, trace accuracy)
  and to demo outcomes.
- Clarified **market differentiation** and customer value narrative around trace-linked RCA.

### How to Improve

- Add concise **3Cs (Company/Customer/Competitor)**: position against eval tools (strength: trace
  RCA; gap: number of attack patterns), include value pricing bands.
- Include **Porter’s Five Forces** bullets (supplier: models; buyers: enterprise AI; threat:
  in-house testing; substitutes: manual QA; rivalry: emerging eval platforms).
- Add **hackathon-specific success story** template (before/after scores, fix time saved) to use in
  demo and README.

______________________________________________________________________

## 3) **PRD_AgentEval.md**

### What Changed

- Standardized **metric naming** (avoid duplicate “Coherence” by distinguishing *Response Coherence*
  vs. *Multi‑Agent Coherence*).
- Harmonized **acceptance criteria** with realistic MVP scope: curated attack counts and performance
  targets that match sprint capacity.
- Added **reporting/export guarantees** (PDF/JSON/CSV) with timing budget.

### How to Improve

- Replace absolute attack counts with **MVP-grade targets** plus growth path:
  - MVP: **60–80 curated patterns** spanning 4 categories with mutations.
  - Post‑MVP: expand via evolutionary generation + shared KB.
- Add **error taxonomy** (Timeout, Rate Limit, Tool Skipped, Token Limit, Upstream 5xx) mapped to
  recommendations.
- Include **API error codes** & examples (400/401/429/5xx) and rate‑limit headers.

______________________________________________________________________

## 4) **AGILE_Implementation.md**

### What Changed

- Confirmed **2‑day sprint cadence** with velocity 20–25 points; ensured test strategy aligns to PRD
  acceptance.
- Expanded **DoD** to enforce coverage, docs, staging deployment, and PO sign‑off.

### How to Improve

- Add **Definition of Ready (DoR)** (story has ACs, test notes, data fixtures, trace tags) to reduce
  churn.
- Create **Risk Kanban** (Trigger → Mitigation → Owner) surfaced in daily standups.
- Add **Test Charters** per epic (persona realism, red-team detection, RCA accuracy).
- Attach **mock datasets** for personas/attacks and a **seeded target app** profile.

______________________________________________________________________

## 5) **TAD_Technical_Architecture.md**

### What Changed

- Clarified **OTel/X‑Ray** data flow and span taxonomy (LLM call, DB, tool, API), and added
  sequence/class refinements for Orchestrator/StateManager.
- Documented **W3C Trace Context** propagation and required headers.

### How to Improve

- Add **Bedrock AgentCore usage** explicitly (primitive: tool‑use/action group for target calls;
  knowledge base optional), and list chosen **AWS Region** with service availability note.
- Tighten IAM to **model‑scoped ARNs** and least privilege; document **Secrets Manager** paths.
- Include **deployment variants**: single‑tenant (per‑customer) vs. multi‑tenant (namespace per
  campaign) and their DynamoDB keys/GSIs.
- Provide **capacity planning sheet** (campaigns → ECS tasks → cost per hour) and **SLA/SLO**
  targets.

______________________________________________________________________

## 6) **PROGRESS_CHECKLIST.md**

### What Changed

- Elevated **production deployment** and **demo video** as critical path with owners and exit
  criteria.
- Linked items to concrete **evidence** (dashboards, ECR tags, X‑Ray traces, S3 report objects).

### How to Improve

- Add **evidence links** columns and **proof‑of‑completion** artifacts.
- Insert **pre‑submission dry run** (fresh deploy + run sample campaign + export PDF) and a
  **rollback drill**.
- Add **cost guardrails** (CloudWatch + Budgets alert for anomaly spikes during demo runs).

______________________________________________________________________

## 🔁 Consistency Fixes to Apply Across Docs

1. **Python-first everywhere:** ensure examples (SDK, CLI, snippets) use Python 3.11 async idioms.
1. **Metrics naming:** distinguish *Response Coherence* vs *Multi‑Agent Coherence*; keep scales
   uniform (1–10, 10 = better).
1. **Attack scope:** set MVP counts (60–80 curated); phrase OWASP coverage as **category coverage**
   rather than exact %.
1. **Trace RCA:** standard template for failure chains + recommendations with
   difficulty/impact/priority.
1. **API/CLI parity:** endpoints in PRD match CLI verbs; surface in AGENTS.md cheat sheet.
1. **DoR & DoD:** embed both in Agile doc and reference in PRD acceptance.

______________________________________________________________________

## ✅ Ready-to-Apply Edits for **AGENTS.md v1.2** (Summary)

- Add **Python + FastAPI + aioboto3** setup block (env, run, deploy).
- Insert **JTBD alignment grid** (above) and link to PRD sections.
- Embed **Quick RCA guide** (where to find spans, common issues, what to change).
- Append **API & CLI quick tables** and **runbook**.

*(I can now regenerate AGENTS.md v1.2 with these changes, or apply them directly in your file
set—your call.)*
