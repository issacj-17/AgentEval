# AWS AI Agent Hackathon Submission Packet – Fillable Template

> Use this template to complete every required deliverable before final submission. Replace
> bracketed text and add additional rows where needed. Keep copies of signed PDFs in
> `req-docs/signatures/`.

______________________________________________________________________

## 1. Devpost Project Summary

- **Project Title:** `[AgentEval – Trace-Aware GenAI Evaluation Platform]`
- **One-Line Tagline (≤140 characters):**
  `[Automated GenAI QA with AWS Bedrock & X-Ray trace insights]`
- **Elevator Pitch (≈100 words):**
  ```text
  [Describe the problem, solution, and key differentiator. Reference value metrics and AWS services.]
  ```
- **Long Description (≈500 words):**
  - Problem & Opportunity: `[ ]`
  - Solution Overview: `[ ]`
  - Key Features: `[ ]`
  - Technical Architecture: `[ ]`
  - Impact & Future Roadmap: `[ ]`
- **Screenshots/GIFs (filenames + captions):**
  | File                          | Caption                   | Notes                   |
  | ----------------------------- | ------------------------- | ----------------------- |
  | `docs/media/arch-diagram.png` | `[Architecture overview]` | `[Uploaded to Devpost]` |
  |                               |                           |                         |

______________________________________________________________________

## 2. Team & Eligibility (Section 3)

- **Team Roster**

  | Name         | Email                | Country/Region | Affiliation           | Role             |
  | ------------ | -------------------- | -------------- | --------------------- | ---------------- |
  | `[Jane Doe]` | `[jane@example.com]` | `[Singapore]`  | `[AgentEval Pte Ltd]` | `[Product Lead]` |
  |              |                      |                |                       |                  |

- **Eligibility Statements (Initials)**

  | Statement                                          | Initials |
  | -------------------------------------------------- | -------- |
  | I am 18+ or age of majority.                       | `[JD]`   |
  | I do not reside in a restricted country/region.    | `[ ]`    |
  | No ties to AWS/Devpost/judges as employee/agency.  | `[ ]`    |
  | Immediate family no conflict.                      | `[ ]`    |
  | I agree to Official Rules and Devpost ToS.         | `[ ]`    |
  | No prohibited sponsor funding prior to Sep 8 2025. | `[ ]`    |

- **Disclosures**

  | Item                                        | Response        |
  | ------------------------------------------- | --------------- |
  | Prior AWS credits/funding before Sep 8 2025 | `[None]`        |
  | Relationships with judges or sponsors       | `[None]`        |
  | Other submissions of same project           | `[None / URLs]` |

- **Signature Log**

  | Name | Signature (link to PDF) | Date (SGT) |
  | ---- | ----------------------- | ---------- |
  |      |                         |            |

______________________________________________________________________

## 3. AWS Usage & Architecture Evidence (Section 4)

- **Regions Used:** `[us-east-1]`

- **Accounts / IDs:** `[Account ID]`

- **Bedrock Models:** `[anthropic.claude-haiku-4-5-20251001-v1:0; amazon.nova-pro-v1:0]`

- **AgentCore/Nova/Q/Strands Components:** `[Tracer baggage, AgentCore headers via tracer.py]`

- **Additional AWS Services:**

  | Service     | Purpose          | Evidence (file/line or log)        |
  | ----------- | ---------------- | ---------------------------------- |
  | DynamoDB    | Campaign state   | `src/agenteval/aws/dynamodb.py`    |
  | S3          | Reports storage  | `src/agenteval/aws/s3.py`          |
  | EventBridge | Lifecycle events | `src/agenteval/aws/eventbridge.py` |
  | X-Ray       | Trace retrieval  | `src/agenteval/aws/xray.py`        |

- **Infrastructure/IaC Links:** `[infrastructure/cloudformation/main.yaml]`

- **Agent Tool Integrations:** `[httpx clients, external APIs]`

______________________________________________________________________

## 4. Deployment & Judge Access (Section 4 Submission Requirements)

- **Public URL:** `[https://demo.agenteval.dev]`

- **Environment Availability Window:** `[Oct 14 2025 – Nov 13 2025]`

- **Credentials:**

  | Role         | Username                | Password/API Key  | Delivery Method                            |
  | ------------ | ----------------------- | ----------------- | ------------------------------------------ |
  | Judge Viewer | `[judge@agenteval.dev]` | `[SecurePass123]` | `[Secure share / Devpost private message]` |
  | API Key      | `X-API-Key`             | `[abc123]`        | `[ ]`                                      |

- **Health Check Endpoints:** `GET /api/v1/health/live`, `GET /api/v1/health/ready`

- **Reset Procedure:** `[POST /api/v1/admin/reset-demo]`

- **Contingency Plan:** `[Docker compose fallback, local instructions path]`

______________________________________________________________________

## 5. Demo Video Metadata (≤3 minutes)

- **Title:** `[AgentEval Live Demo]`
- **Link (YouTube/Vimeo):** `[https://youtu.be/... ]`
- **Duration:** `[2:58]`
- **Recording Date (SGT/PT):** `[2025-10-20 22:00 SGT / 2025-10-20 07:00 PT]`
- **Caption File:** `[req-docs/video_plan/captions-en.vtt]`
- **Background Audio License:** `[req-docs/licenses/song-license.pdf]`

______________________________________________________________________

## 6. Testing & Evidence Package

- **Automated Tests:**

  | Command     | Result           | Timestamp                | Log Path                                |
  | ----------- | ---------------- | ------------------------ | --------------------------------------- |
  | `pytest -q` | `[216/216 pass]` | `[2025-10-19 01:15 SGT]` | `req-docs/evidence/pytest-20251019.log` |

- **Live Demo Run:**

  | Script                                        | Outcome     | Artefacts                                       |
  | --------------------------------------------- | ----------- | ----------------------------------------------- |
  | `scripts/run-live-demo.sh --region us-east-1` | `[Success]` | `demo/evidence/pulled-reports/20251019T032317/` |

- **Trace Exports:** `[demo/evidence/trace-reports/*.json]`

______________________________________________________________________

## 7. Licensing & Third-Party Assets (Sections 4 & 7)

- **Open Source Dependencies:** (export from SBOM)

  | Package   | Version | License | Notes                     |
  | --------- | ------- | ------- | ------------------------- |
  | `fastapi` | `[ ]`   | MIT     | `[Included in NOTICE.md]` |

- **Media Assets:**

  | Asset                     | Source URL      | License       | Proof (path)                  | Usage      |
  | ------------------------- | --------------- | ------------- | ----------------------------- | ---------- |
  | `[Background music name]` | `[https://...]` | `[CC-BY 4.0]` | `req-docs/licenses/music.pdf` | Demo video |

______________________________________________________________________

## 8. Financial / Preferential Support

- **AWS Promo Credits (requested/received):** `[Yes/No – include amount and confirmation ID]`
- **Other Sponsor/Admin consideration:** `[None]`
- **Statement:**
  ```text
  [Confirm no prohibited funding or preferential support prior to submission period.]
  ```

______________________________________________________________________

## 9. Submission Freeze & Change Control (Section 5)

- **Release/Code Freeze Dates:** `[Feature freeze Oct 18, Code freeze Oct 19]`

- **Responsible Owners:**

  | Role            | Owner | Contact |
  | --------------- | ----- | ------- |
  | Release Manager | `[ ]` | `[ ]`   |

- **Post-Deadline Policy Confirmation:** `[Yes – only IP/PII removals allowed after deadline]`

- **Sign-off Document:** `[req-docs/signatures/SUBMISSION_FREEZE_SIGNOFF.pdf]`

______________________________________________________________________

## 10. Change Log Since Sep 8 2025

- **Summary Table:**

  | Date (PT)      | Commit/PR       | Description                   | Modules               | Reviewer |
  | -------------- | --------------- | ----------------------------- | --------------------- | -------- |
  | `[2025-10-11]` | `[DI-Refactor]` | `[Comprehensive DI refactor]` | `[container.py, ...]` | `[ ]`    |

- **Evidence Attachments:**

  | Artifact        | Path                             |
  | --------------- | -------------------------------- |
  | Git log         | `req-docs/evidence/git-log.txt`  |
  | CI/Test Reports | `req-docs/evidence/pytest-*.log` |

______________________________________________________________________

## 11. Multiple Submissions Disclosure

- **Other Hackathons/Challenges using AgentEval:** `[None / list]`
- **Differentiation Summary:**
  ```text
  [If multiple submissions exist, describe unique features, datasets, or delivery differentiators for each.]
  ```

______________________________________________________________________

## 12. Support & Monitoring Plan (Judging Window)

- **On-Call Schedule:** `[Name, timezone, coverage hours]`
- **Support Channels:** `support@agenteval.dev`, Slack `#hackathon-support`
- **Uptime Monitoring:** `[Tool/dashboard link]`
- **Credential Rotation Plan Post-Judging:** `[Describe rotation date/process]`

______________________________________________________________________

## 13. Privacy & Publicity Acknowledgement (Sections 9–15)

- **Statement Added to README/Devpost:**
  ```text
  By submitting AgentEval, we agree to the AWS AI Agent Global Hackathon Official Rules, Devpost Terms of Service, and the publicity and privacy provisions therein.
  ```
- **Data Handling Notes:** `[No PII stored; demo data reset nightly at 03:00 SGT]`
- **Privacy Policy Reference:** `[Link to company privacy notice]`

______________________________________________________________________

## 14. Submission Checklist Sign-off

- **Final Reviewer:** `[Name]`
- **Date (SGT):** `[ ]`
- **All Required Artefacts Uploaded:** `☐`
- **Devpost Draft Reviewed by Peers:** `☐`
- **Backup Archive Stored (path):** `[req-docs/submission/AgentEval_submission_20251020.zip]`
