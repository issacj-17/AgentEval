# Judging Scorecard – 2025-10-18 (Post Live Demo)

| Criterion | Weight | Self-Score | Current Evidence | Upgrade Actions |
| --- | --- | --- | --- | --- |
| Technical Execution | 50 | 34 | `source .venv/bin/activate && pytest -q` → 739 pass, 0 fail, overall coverage 70 % (`htmlcov/index.html`); Bedrock/DynamoDB/S3/EventBridge/X-Ray integrations exercised in suite | Push targeted tests for low-coverage modules (tracer, orchestration, AWS clients) to reach ≥80 %; rerun live demo for runtime telemetry screenshots. |
| Potential Value/Impact | 20 | 17 | README value story (`README.md`:11-48) + BRD/PRD alignment (`req-docs/BRD_AgentEval.md`, `req-docs/PRD_AgentEval.md`) | Add quantified customer testimonial/ROI table to README & Devpost entry. |
| Functionality | 10 | 5 | Latest evidence dashboard (`demo/evidence/live-demo-latest.md`:1-27) shows 0 % success due to stale run; automation scripts ready (`scripts/run-live-demo.sh`) | Execute fresh live demo, confirm successful turns, update dashboard + log references, and document judge credential flow. |
| Demo Presentation | 10 | 0 | No ≤3 min walkthrough video yet; storyboard only (`req-docs/video_plan/video_storyboard.md`) | Record/edit demo video, upload (unlisted), attach captions + licensed audio proof, link in SUBMISSION_GUIDE & Devpost draft. |
| Creativity | 10 | 9 | AgentCore trace linkage captured in code (`src/agenteval/observability/tracer.py`:370-428) & tests (`tests/unit/test_trace_analyzer.py`) | Capture span visualization/X-Ray screenshots for inclusion in video and submission collateral. |

Revisit scorecard after Bedrock profile + demo target fixes and once the video is published.
