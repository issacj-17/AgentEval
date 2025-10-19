# AgentEval Compliance & Readiness Audit – 2025-10-18 (22:55–22:51 SGT)

## Automated Test Suite

- Command: `pytest -q`
- Outcome: ✅ 216/216 tests passed (~15 s)
- Coverage: 44 % overall (see `htmlcov/`); warnings limited to Pydantic deprecation + async mocks;
  OTEL exporter warns because no local collector is running.

## Live Demo Execution

- Commands:
  1. `scripts/setup-live-demo.sh --region us-east-1`
  1. `scripts/run-live-demo.sh --region us-east-1 --skip-verify` (full run, logs captured in
     `demo/evidence/live-demo-logs/`)
  1. `scripts/teardown-live-demo.sh --region us-east-1 --force`
- Outcome: ✅ Pipeline completes end-to-end (campaign creation, DynamoDB state, S3 results/reports,
  EventBridge events, X-Ray traces). Cloud resources were torn down afterward.
- Notes:
  - Bedrock fallbacks now automatically downgrade to Titan models when inference profiles are
    unavailable. Warnings are emitted but execution succeeds without retries.
  - Demo target defaults to `https://postman-echo.com/post` (configurable via `DEMO_TARGET_URL`) and
    is verified before campaigns execute, preventing DNS failures.
  - `--skip-verify` bypasses the optional ECS stack check. Run `scripts/check-aws-services.sh` if
    you provision ECS resources.

S3 artefacts from the run (before teardown):

- `s3://agenteval-results-585049192332/campaigns/e8269ff9-ceaa-476f-911c-22b36aea8dc4/results.json`
- `s3://agenteval-reports-585049192332/reports/e8269ff9-ceaa-476f-911c-22b36aea8dc4/demo-report-20251019-012657.json`

These objects were removed during teardown; regenerate as needed for final evidence.

## Outstanding Gaps

1. **Bedrock Inference Profiles (Optional)** – Fallback models are in place; supply official
   inference profile ARNs if the final submission must showcase Claude/Nova directly.
1. **Judge Access Package** – Update `req-docs/JUDGE_ACCESS.md` with the new target URL and
   credentials before sharing with reviewers.
1. **Eligibility Documentation** – `req-docs/TEAM_INFO.md`, compliance checklist, and disclosures
   still blank.
1. **Demo Video & Submission Assets** – No ≤3 min video or updated Devpost entry yet.

## Action Plan

| Owner      | Task                                                                                                                 | Due              |
| ---------- | -------------------------------------------------------------------------------------------------------------------- | ---------------- |
| DevOps     | Decide whether to keep Titan fallback or provision official inference profiles; re-run demo if configuration changes | Oct 19 22:00 SGT |
| Docs Lead  | Update README, SUBMISSION_GUIDE, JUDGE_ACCESS with current target URL/credentials                                    | Oct 20 00:00 SGT |
| People Ops | Complete TEAM_INFO roster & disclosures                                                                              | Oct 19 12:00 SGT |
| Product    | Produce ≤3 min video highlighting successful live demo                                                               | Oct 20 12:00 SGT |

## Evidence References

- `pytest -q` (2025-10-19 01:15 SGT) – 216 pass, 44 % coverage
- `demo/evidence/live-demo-logs/` – full live demo runs with Titan fallback and reachable target
- `demo/evidence/pulled-reports/` – synced DynamoDB + S3 artefacts from the latest demo run
- `demo/evidence/trace-reports/` – X-Ray trace archives for profiling and debugging
- `scripts/setup-live-demo.sh` / `scripts/teardown-live-demo.sh` console outputs (same session)

Repeat live demo after addressing Bedrock profile and demo target to replace warnings with clean
success evidence.
