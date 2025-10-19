# Judge Access & Testing Instructions

Provide this document (or a copy) in the Devpost submission so judges can evaluate the project without requesting additional information.

## 1. Deployment URL

- **Environment:** `https://postman-echo.com/post` _(default demo target; replace with production URL when available)_  
- **Availability:** 24/7 uptime from Oct 14 2025 to Nov 13 2025 08:00 SGT (Oct 12 2025 to Nov 12 2025 17:00 PT).

## 2. Credentials

| Role | Username | Password / API Key | Notes |
| --- | --- | --- | --- |
| Judge Viewer | _TBD_ | _TBD_ | Provide read-only dashboard access credentials before submission |
| API Key | `X-API-Key` header | _TBD_ | Securely share evaluation key covering `/api/v1/*` endpoints |

Provide secure delivery of secrets (e.g., via Devpost private message or secure share). Rotate credentials after judging.

## 3. Test Data Reset

- Automated reset runs nightly at 03:00 SGT.  
- Manual reset endpoint: `POST /api/v1/admin/reset-demo` (protected by API key).

## 4. Evaluation Script

1. Log into the web dashboard with the judge account.  
2. Start a persona campaign targeting the sample chatbot.  
3. Observe trace correlation view and export PDF report.  
4. Review red-team findings and remediation suggestions.  
5. Verify health endpoints:  
   - `GET /api/v1/health/live`  
   - `GET /api/v1/health/ready`

## 5. Technical Requirements

- Modern browser (Chrome/Edge/Safari)  
- No additional plugins required  
- API latency budget: <200 ms p95 (observed)  
- Supported AWS regions: `us-east-1` (Bedrock), `us-west-2` (SageMaker fallback)

## 6. Support Contact

- Email: support@agenteval.dev  
- Slack: `#hackathon-support` (invitation link included in submission)  
- On-call engineer (Oct 20–Nov 13): +65-0000-0000

## 7. Contingency

If the hosted environment becomes unavailable, provide judges with:

- Docker Compose stack (`infrastructure/docker/compose.yaml`)  
- Seed data scripts to replay sample campaign (`scripts/demo_seed.py`)  
- Instructions to run locally with mocked AWS services (see `req-docs/TEST_DEMO_PLAYBOOK.md`)
