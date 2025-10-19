# AgentEval Demo Video Storyboard (≤3 minutes)

## Overview

- **Audience:** AWS AI Agent Hackathon judges, enterprise buyers evaluating GenAI QA solutions.
- **Goal:** Demonstrate AgentEval’s unique trace-based evaluation workflow running on AWS Bedrock,
  while mapping directly to judging criteria (Technical Execution, Value, Functionality, Creativity,
  Demo).
- **Format:** 3-minute voice-over screen capture with on-screen callouts; background music optional
  (license required).

## Scene Breakdown

| Time (mm:ss) | Scene                 | Visuals                                                                                                                                               | Script Highlights                                                                                                                                                                                                                       | Call-to-Action                                                                         |
| ------------ | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 0:00-0:15    | Cold Open             | Animated title: “AgentEval — Autonomous GenAI Evaluation on AWS” over architecture diagram highlights                                                 | “Enterprises struggle to trust GenAI. AgentEval is the first autonomous evaluation platform that links agent performance to AWS X-Ray traces, so teams know exactly where failures happen.”                                             | Display AWS + AgentEval logos (per guidelines)                                         |
| 0:15-0:45    | Problem & Value       | Slides or B-roll of dashboards; overlay failure stats                                                                                                 | “85% of GenAI rollouts miss quality targets. AgentEval cuts validation time by 70% while catching 95% of safety regressions.”                                                                                                           | Subtitle with value metrics                                                            |
| 0:45-1:15    | Architecture Snapshot | Pan across `architecture/diagram.md` rendered to PNG; highlight Bedrock, DynamoDB, EventBridge, X-Ray                                                 | “We’re 100% on AWS: Bedrock for Claude/Nova reasoning, DynamoDB & S3 for state, EventBridge for orchestration, X-Ray for root-cause analytics.”                                                                                         | Label AgentCore traces & tool integrations                                             |
| 1:15-2:15    | Live Demo Walkthrough | Record terminal running `scripts/run-live-demo.sh --region us-east-1`; switch to generated `demo/evidence/live-demo-latest.md`; show trace drill-down | “Persona agents invoke Bedrock via our async client, red teams attack the target API, judges score every turn, and Trace Analyzer maps failures to AWS X-Ray spans. Here’s the S3 artefact auto-synced for judges.”                     | Highlight `demo/evidence/pulled-reports/...` path and missing trace steps to remediate |
| 2:15-2:45    | Differentiators       | Show UI or Markdown dashboards; annotate features                                                                                                     | “Only AgentEval combines personas, red teaming, and traces. We inject AgentCore headers to correlate every call (`src/agenteval/observability/tracer.py`). Titan fallbacks guarantee Bedrock coverage even without inference profiles.” | Overlay code snippets / bullet callouts                                                |
| 2:45-3:00    | Call to Action        | Return to title card with URL + credentials                                                                                                           | “Access the live deployment at `<final URL>`. Judges can log in with the credentials provided. We welcome feedback and are ready for AWS Marketplace onboarding.”                                                                       | Display support email + Slack channel                                                  |

## Capture Checklist

- Record in 1080p, 30 fps; disable personal notifications.
- Use OBS or QuickTime; capture mic + system audio.
- Keep mouse movements deliberate; zoom into terminal/text when referencing evidence paths.
- After recording, add captions for accessibility; confirm video length ≤3:00.
- Upload to YouTube (unlisted) with description linking to repo, deployment URL, and credential note
  (no secrets). Store link in `SUBMISSION_GUIDE.md` and Devpost form.

## Supporting Assets Needed

- Architecture diagram PNG export (from `architecture/diagram.md`).
- Latest demo artefacts (`demo/evidence/`), including trace exports (ensure missing trace entries
  resolved before capture).
- Short testimonial quote or metric overlay (optional).
- Background track license saved to `req-docs/licenses/` if used.

## Voiceover Script Notes

1. **Hook:** Pain point & promise (value criterion).
1. **Technical Depth:** Mention Bedrock invoke paths, EventBridge events, DynamoDB tables (technical
   criterion).
1. **Functionality Proof:** Show completed campaigns + artefacts (functionality criterion).
1. **Creativity Angle:** Trace correlation / AgentCore integration (creativity criterion).
1. **Ask:** Provide deployment access, invite judges (demo criterion).

## Post-Production Checklist

- Trim intro/outro dead air; normalize audio levels (~-14 LUFS).
- Add lower-thirds for speaker name/company.
- Insert on-screen text for key stats & service names.
- Final review for licensing, trademark compliance, absence of sensitive data.
