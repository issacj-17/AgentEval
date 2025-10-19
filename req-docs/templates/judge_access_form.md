# Judge Access Package Template

## 1. Deployment Information
- **Primary URL:** `[https://...]`
- **Environment Description:** `[Staging/Production clone]`
- **Availability Window:** `[Oct XX – Nov XX]`
- **Expected Latency / Capacity:** `[p95 <200ms, 100 concurrent sessions]`

## 2. Credentials & Secrets Delivery
| Role | Username | Password/API Key | Permissions | Delivery Method |
| --- | --- | --- | --- | --- |
| Judge Viewer |  |  |  |  |
| Admin (if required) |  |  |  |  |
| API Key | `X-API-Key` |  | `GET /api/v1/*` |  |

- **Secret Sharing Method:** `[Devpost private message / AWS Secrets Manager share / encrypted email]`
- **Rotation Date:** `[e.g., Nov 14 2025]`

## 3. Testing Checklist
1. Login to dashboard → `[URL/path]`
2. Launch persona campaign → `[Button/path]`
3. Review trace correlation → `[Screenshot reference]`
4. Download report → `[S3 path or link]`
5. Verify health endpoints → `GET /api/v1/health/live`, `GET /api/v1/health/ready`

## 4. Reset & Maintenance Procedures
- Nightly reset schedule: `[03:00 SGT via cron job]`
- Manual reset endpoint: `POST /api/v1/admin/reset-demo`
- Sample CLI command: `curl -H "X-API-Key: ____" -X POST https://.../reset-demo`

## 5. Support & Escalation
| Channel | Contact | Coverage |
| --- | --- | --- |
| Email | `support@...` | `[24h response]`
| Slack | `#hackathon-support` | `[Oct 20 – Nov 13]`
| On-call | `[Name, phone]` | `[Timezone / Hours]` |

## 6. Contingency Plan
- Local fallback instructions: `req-docs/TEST_DEMO_PLAYBOOK.md`
- Docker Compose stack: `infrastructure/docker/compose.yaml`
- Mock mode demo: `python demo/agenteval_demo_mock.py`

