# AgentEval Notice

This project is distributed for the AWS AI Agent Global Hackathon 2025.

## Third-Party Notices

AgentEval uses open-source components. The following libraries are included under their respective
licenses:

- FastAPI
- Uvicorn (BSD License)
- Pydantic & pydantic-settings
- boto3 / aioboto3 (Apache License 2.0)
- httpx (BSD License)
- aiofiles (Apache License 2.0)
- OpenTelemetry SDK & instrumentation packages (Apache License 2.0)
- structlog (Apache License 2.0)
- tenacity (Apache License 2.0)
- python-dotenv (BSD License)
- pytest, pytest-asyncio, pytest-cov, pytest-mock
- black
- isort
- flake8
- mypy

Full license texts are available from the respective upstream projects. A generated Software Bill of
Materials (SBOM) should be produced for each release using `uv pip list --format=freeze` or
CycloneDX tooling (see `req-docs/COMPLIANCE_CHECKLIST.md`).

## AWS Services

AgentEval integrates with Amazon Web Services, including Amazon Bedrock, Amazon SageMaker
(optional), Amazon DynamoDB, Amazon S3, Amazon EventBridge, and AWS X-Ray. Usage of these services
is governed by the AWS Customer Agreement and the specific service terms. Ensure that all AWS
credentials are provisioned via AWS IAM roles or AWS Secrets Manager; do not commit credentials to
source control.

## Media and Assets

All media (icons, video soundtracks, and screenshots) included in submissions must be properly
licensed. Store proof of licenses in `req-docs/ASSET_LICENSES.md`.
