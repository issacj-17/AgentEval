# AgentEval Live Demo Runbook

This guide captures the full start-to-finish workflow for the AWS-backed live demo. It includes
prerequisites, execution steps, validation checks, and teardown, along with the results of the most
recent execution attempt in this workspace.

## Prerequisites

- **Python 3.11+** with virtual environment created and activated
  ```bash
  # Create virtual environment
  python3 -m venv .venv  # or use: uv venv

  # CRITICAL: Activate before running any scripts
  source .venv/bin/activate  # On Windows: .venv\Scripts\activate
  ```
- Project dependencies installed: `pip install -e ".[dev]"` or `uv pip install -e ".[dev]"`
- AWS CLI v2 configured with credentials that can create and delete DynamoDB, S3, EventBridge,
  Bedrock, and X-Ray resources
  - Verify with `aws sts get-caller-identity`
- `.env.live-demo` populated with the correct resource names and model identifiers (the setup script
  generates a template if missing)
- Optional helpers: `jq` (for JSON parsing) and `uv` (for dependency management)

## End-to-End Workflow

1. **Environment sanity check**

   ```bash
   # CRITICAL: Always activate virtual environment first!
   source .venv/bin/activate        # On Windows: .venv\Scripts\activate

   pip install -e ".[dev]"          # Ensure dependencies are present
   aws sts get-caller-identity      # Confirm credentials
   ./scripts/verify-live-demo-setup.sh
   ```

1. **Provision AWS resources (one-time setup)**

   ```bash
   ./scripts/setup-live-demo.sh --region us-east-1
   ```

   - Creates DynamoDB tables, S3 buckets, and EventBridge bus
   - Verifies Bedrock model access (skip via `--skip-bedrock` if desired)
   - Generates `.env.live-demo` template if not present

1. **Run the live demo with chatbot**

   **Option A: Full orchestration script (recommended)**

   ```bash
   # Automatically starts Nebula chatbot and runs complete evaluation
   ./scripts/run-full-demo.sh --region us-east-1 --skip-setup

   # Options:
   #   --skip-setup     Skip AWS infrastructure provisioning (if already done)
   #   --quick          Campaign creation only, no turn execution
   #   --auto-teardown  Automatically clean up AWS resources after demo
   #   --skip-pull      Skip results pulling
   ```

   **Option B: Direct chatbot demo (more control)**

   ```bash
   python demo/agenteval_chatbot_demo.py --region us-east-1

   # Options:
   #   --quick                Run in quick mode (no turn execution)
   #   --use-existing-server  Connect to already-running chatbot (port 5057)
   ```

   **What happens:**

   - Automatically starts the Nebula banking assistant chatbot (FastAPI on port 5057)
   - Runs 10 persona campaigns (frustrated_customer, technical_expert, elderly_user, etc.)
   - Runs 1 red-team campaign (injection, jailbreak attacks)
   - Each campaign executes 3 turns with the live chatbot
   - Judge agent evaluates all 11 metrics per turn
   - Generates HTML dashboard with interactive drill-down
   - Pulls all results to local `outputs/` directory
   - Automatically stops chatbot when complete

1. **Inspect results**

   **View interactive HTML dashboard:**

   ```bash
   # Open in browser (shows all campaigns with drill-down)
   open outputs/latest/reports/dashboard.html

   # Click "View Details" on any campaign to see:
   #   - Actual chatbot responses (Nebula banking assistant)
   #   - Turn-by-turn user messages and system responses
   #   - All 11 evaluation metrics with scores, reasoning, evidence
   #   - Pass/fail status and trace IDs for debugging
   ```

   **View markdown reports:**

   ```bash
   cat outputs/latest/dashboard.md
   cat outputs/latest/summary.md
   ```

   **AWS health check:**

   ```bash
   ./scripts/check-aws-services.sh --region us-east-1 --json | jq .
   ```

1. **Teardown resources**

   ```bash
   ./scripts/teardown-live-demo.sh --region us-east-1
   ```

   - Use `--force` to skip confirmation
   - `--keep-tables` or `--keep-buckets` preserve data but empty contents

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

1. `scripts/run-live-demo.sh --region us-east-1`

   - Health check surfaced expected warnings for unused resources (CloudFormation stack, ECS
     cluster, cost explorer).
   - Ran two full campaigns; outputs streamed in
     `demo/evidence/live-demo-logs/run-20251019T023534.log`.
   - Artefacts pulled to `demo/evidence/pulled-reports/20251019T023832`, with summaries in
     `demo/evidence/live-demo-latest.md` and `demo/evidence/dashboard.md`.
   - Persona, red-team, and judge messages now distinct from system responses; echoed responses are
     annotated with an `(echo)` prefix.

1. `scripts/teardown-live-demo.sh --region us-east-1`

   - No manual input provided; the 10-second confirmation timeout elapsed and teardown continued
     automatically.
   - Deleted the DynamoDB tables, S3 buckets, and EventBridge bus while preserving `.env.live-demo`.

1. Post-run verification: `scripts/check-aws-services.sh --region us-east-1 --quiet`

   - Confirmed that demo resources were removed and Bedrock access remains available.

All steps completed successfully; the environment is clean and the latest evidence reflects the
corrected logging behavior.
