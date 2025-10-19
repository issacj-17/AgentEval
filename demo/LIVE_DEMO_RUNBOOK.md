# AgentEval Live Demo Runbook

This guide captures the full start-to-finish workflow for the AWS-backed live demo. It includes prerequisites, execution steps, validation checks, and teardown, along with the results of the most recent execution attempt in this workspace.

## Prerequisites
- Python 3.9+ with project dependencies installed: `pip install -e ".[dev]"` (within an activated virtualenv).
- AWS CLI v2 configured with credentials that can create and delete DynamoDB, S3, EventBridge, Bedrock, and X-Ray resources.
  - Verify with `aws sts get-caller-identity`.
- `.env.live-demo` populated with the correct resource names and model identifiers (the setup script now prints a template instead of overwriting your file).
- Optional helpers: `jq` (for JSON parsing) and `uv` (for dependency management).

## End-to-End Workflow
1. **Environment sanity check**
   ```bash
   source .venv/bin/activate        # if not already active
   pip install -e ".[dev]"          # ensure dependencies are present
   aws sts get-caller-identity      # confirm credentials
   scripts/verify-live-demo-setup.sh
   ```

2. **Provision AWS resources**
   ```bash
   scripts/setup-live-demo.sh --region us-east-1
   ```
   - Creates DynamoDB tables, S3 buckets, and EventBridge bus.
   - Verifies Bedrock model access (skip via `--skip-bedrock` if desired).
   - Confirms `.env.live-demo` is present without overwriting it.

3. **Run the live demo**
   ```bash
   scripts/run-live-demo.sh --region us-east-1
   ```
   - Delegates to `python -m agenteval.cli.live_demo`.
   - Use `--auto-teardown` to clean up automatically or `--quick` for campaign creation only.

4. **Inspect results**
   ```bash
   scripts/check-aws-services.sh --region us-east-1 --json | jq .
   ```
   - The orchestrator already downloads artefacts to `demo/evidence/pulled-reports/<timestamp>` and generates dashboards in `demo/evidence/`.
   - Use the health check for post-run verification and cost-awareness.

5. **Teardown resources**
   ```bash
   scripts/teardown-live-demo.sh --region us-east-1
   ```
   - Use `--force` to skip confirmation.
   - `--keep-tables` or `--keep-buckets` preserve data but empty contents.

## Validation Checklist
- DynamoDB tables `agenteval-*` exist and contain campaign data.
- S3 buckets `agenteval-results-*` and `agenteval-reports-*` populated with artefacts.
- EventBridge bus `agenteval` present and receiving events.
- Bedrock model access validated for persona, red-team, and judge roles.
- X-Ray traces captured during the demo run.

## Latest Execution (2025-10-19T02:35Z)
Commands were executed from the repository root with the virtual environment active.

1. `scripts/setup-live-demo.sh --region us-east-1`
   - Created/verified four DynamoDB tables, two S3 buckets, and the `agenteval` EventBridge bus.
   - Confirmed Bedrock model access for persona, red team, judge, and fallback models.
   - Preserved the existing `.env.live-demo`.

2. `scripts/run-live-demo.sh --region us-east-1`
   - Health check surfaced expected warnings for unused resources (CloudFormation stack, ECS cluster, cost explorer).
   - Ran two full campaigns; outputs streamed in `demo/evidence/live-demo-logs/run-20251019T023534.log`.
   - Artefacts pulled to `demo/evidence/pulled-reports/20251019T023832`, with summaries in `demo/evidence/live-demo-latest.md` and `demo/evidence/dashboard.md`.
   - Persona, red-team, and judge messages now distinct from system responses; echoed responses are annotated with an `(echo)` prefix.

3. `scripts/teardown-live-demo.sh --region us-east-1`
   - No manual input provided; the 10-second confirmation timeout elapsed and teardown continued automatically.
   - Deleted the DynamoDB tables, S3 buckets, and EventBridge bus while preserving `.env.live-demo`.

4. Post-run verification: `scripts/check-aws-services.sh --region us-east-1 --quiet`
   - Confirmed that demo resources were removed and Bedrock access remains available.

All steps completed successfully; the environment is clean and the latest evidence reflects the corrected logging behavior.
