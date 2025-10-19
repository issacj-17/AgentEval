# AgentEval Slide Deck Flow (8–10 Slides)

## Slide 1 – Title & Team
- **Headline:** “AgentEval – Trace-Aware GenAI Evaluation on AWS”
- Include team members, roles, and contact email (align with `TEAM_INFO.md`).
- Add hackathon branding + AWS logo per guidelines.

## Slide 2 – Problem & Opportunity
- Statistics on GenAI quality failures (85% miss KPI, 70% rework costs).
- Bullet pain points: slow validation, hidden regressions, compliance risks.
- Visual: bar chart or infographic.

## Slide 3 – Solution Overview
- One-liner value proposition.
- Three pillars (Personas, Red Team, Trace Analysis) with icons.
- Callout for autonomous agent orchestration.

## Slide 4 – Architecture on AWS
- Rendered architecture diagram with labels (Bedrock, DynamoDB, S3, EventBridge, X-Ray, AgentCore headers).
- Annotate data flow arrows (persona → target → judge → trace analyzer).
- Footnote referencing `architecture/diagram.md` for details.

## Slide 5 – Key Features & Differentiators
- Feature table linking to evidence:
  1. Bedrock Claude/Nova + Titan fallback (`src/agenteval/aws/bedrock.py`).
  2. AgentCore observability (`src/agenteval/observability/tracer.py`).
  3. Automated artefact collection (`demo/evidence/...`).
  4. Tool integrations (HTTPx, DynamoDB, EventBridge).
- Highlight uniqueness vs. typical eval platforms.

## Slide 6 – Live Demo Snapshot
- Screenshots: terminal run, dashboard excerpt, trace correlation view.
- Caption referencing upcoming demo video (≤3 min).
- Include link to deployment + credentials (consistent with `JUDGE_ACCESS.md`).

## Slide 7 – Judging Criteria Mapping
- Table with five criteria → evidence + planned enhancement.
- Use same scores as `req-docs/JUDGING_SCORECARD.md` with upgrade bullets.

## Slide 8 – Roadmap & Market Impact
- Roadmap bullets (Marketplace listing, SOC2 readiness, integration partners).
- Market sizing or pilot metrics.
- Optional testimonial or quote.

## Slide 9 – Team & Support Readiness
- Roles & responsibilities (Release/QA/Infra from `SUBMISSION_FREEZE.md`).
- Support channels: email, Slack, on-call window.
- Mention openness to AWS GTM support (prize alignment).

## Slide 10 – Call to Action
- Reiterate deployment URL, repo link, video link, support contact.
- Thank you + prompt for questions.

## Design Notes
- Stick to AWS brand palette (blues/oranges) with high contrast.
- Limit text; favor visuals + keywords (~6 bullets per slide).
- Embed short captions on screenshots citing file paths/evidence.
- Ensure all assets have cleared licenses (track in `req-docs/ASSET_LICENSES.md`).
- Export to PDF for Devpost upload; store source in `req-docs/presentations/` when created.

## Production Checklist
1. Draft slides in Google Slides or PowerPoint; use 16:9.
2. Insert architecture diagram PNG and demo screenshots.
3. Sync messaging with video script to avoid contradictions.
4. Review for confidentiality (no secrets, account IDs).
5. Export PDF + source file; save under versioned filename `AgentEval_Pitch_v1.pptx/pdf`.
