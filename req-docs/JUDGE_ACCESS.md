# Judge Access & Testing Instructions

**Last updated:** 2025-10-22 06:45 SGT

Provide this document (or a copy) in the Devpost submission so judges can evaluate the project
without requesting additional information.

## 1. Deployment URL

- **Current verification target:** `https://postman-echo.com/post` (kept for automated smoke tests).
- **Final judge endpoint:** Dedicated staging environment URL will be published here and on Devpost
  by **Oct 22 2025 18:00 SGT** (Oct 22 2025 03:00 PT) once SSL and monitoring checks pass.
- **Availability:** 24/7 uptime from Oct 14 2025 to Nov 13 2025 08:00 SGT (Oct 12 2025 to
  Nov 12 2025 17:00 PT).

## 2. Credentials

| Role         | Username                                                         | Password / API Key              | Notes                                           |
| ------------ | ---------------------------------------------------------------- | ------------------------------- | ----------------------------------------------- |
| Judge Viewer | _Issued via Devpost private message (ETA Oct 22 2025 18:00 SGT)_ | _Issued with above message_     | Read-only dashboard account with feature parity |
| API Key      | `X-API-Key` header                                               | _Issued with credential bundle_ | Covers `/api/v1/*`; rotated after judging       |

Provide secure delivery of secrets (e.g., via Devpost private message or secure share). Rotate
credentials after judging.

## 3. Test Data Reset

- Automated reset runs nightly at 03:00 SGT.
- Manual reset endpoint: `POST /api/v1/admin/reset-demo` (protected by API key).

## 4. Evaluation Script

1. Log into the web dashboard with the judge account.
1. Start a persona campaign targeting the sample chatbot.
1. Observe trace correlation view and export PDF report.
1. Review red-team findings and remediation suggestions.
1. Verify health endpoints:
   - `GET /api/v1/health/live`
   - `GET /api/v1/health/ready`

## 5. Technical Requirements

- Modern browser (Chrome/Edge/Safari)
- No additional plugins required
- API latency budget: \<200 ms p95 (observed)
- Supported AWS regions: `us-east-1` (Bedrock), `us-west-2` (SageMaker fallback)

## 6. Contingency

If the hosted environment becomes unavailable, provide judges with:

- Docker Compose stack (`infrastructure/docker/compose.yaml`)
- Seed data scripts to replay sample campaign (`scripts/demo_seed.py`)
- Instructions to run locally with mocked AWS services (see `req-docs/TEST_DEMO_PLAYBOOK.md`)
