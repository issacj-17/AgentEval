# AgentEval Deployment Guide

This guide describes how to provision the AgentEval platform infrastructure using either **AWS CloudFormation** (nested stacks) or **OpenTofu/Terraform**. Both paths create the production-quality baseline described in the architecture docs: VPC networking, ECS Fargate compute, DynamoDB/S3 data stores, EventBridge event bus, and the observability stack (CloudWatch + X-Ray).

## Credential & Environment Setup

The instructions below assume you are an AWS administrator for the target account and can create identities and manage IAM policies.

### 1. Pick an identity workflow

- **AWS IAM Identity Center (preferred)**  
  1. In the AWS console, open **IAM Identity Center → Users** and add yourself (or confirm an existing assignment).  
  2. Create/assign a permission set that includes at least: `bedrock:InvokeModel`, `bedrock:InvokeAgent` (if you wire AgentCore), DynamoDB CRUD on the AgentEval tables, S3 access to the results/reports buckets, EventBridge `PutEvents`, CloudWatch Logs write, and the IAM actions needed by your IaC (for ECS/LB roles).  
  3. On your workstation run `aws configure sso` and follow the browser flow. Accept the profile name (e.g. `agenteval-admin`).  
  4. In the project `.env`, set `AWS_REGION=<region>` and `AWS_PROFILE=agenteval-admin`. Leave the direct access key fields blank; the AWS SDK will read the refreshed SSO tokens.

- **IAM user with programmatic access (fallback for non-SSO environments)**  
  1. Console path: **IAM → Users → Add users**. Give the user a descriptive name such as `agenteval-admin`. Select **Access key – Programmatic access** only.  
  2. Attach the minimum policies needed (create fine-grained policies whenever possible):  
     - Bedrock model/agent invocation  
     - DynamoDB access for the AgentEval tables  
     - S3 read/write for results/reports buckets  
     - EventBridge `PutEvents` on the AgentEval bus  
     - CloudWatch Logs write, X-Ray write (if deploying observability)  
     - Any additional IAM permissions required by CloudFormation/OpenTofu (e.g., `iam:CreateRole`, `iam:PassRole`).  
  3. Complete the wizard and **download the `.csv`** with the access key ID/secret key. Store it in a password manager—this is the only time the secret is visible.  
  4. Configure the AWS CLI locally:  
     ```bash
     aws configure --profile agenteval-admin
     # paste the access key, secret, and default region when prompted
     ```  
     Add `AWS_PROFILE=agenteval-admin` to your `.env`. Avoid committing static keys; if you must export them directly, use a credential helper like `aws-vault` and rotate frequently.

### 2. Prepare local configuration

1. Copy the environment template and update required values:
   ```bash
   cp .env.example .env
   ```
   Set `AWS_REGION`, `AWS_PROFILE` (or the access key variables), and align the DynamoDB/S3/EventBridge names with what you will provision.

2. Install project dependencies and bootstrap the virtual environment:
   ```bash
   bash scripts/setup.sh
   ```
   The script installs `uv`, creates `.venv`, installs Python dependencies, and ensures `.env` exists.

3. Validate your identity before deploying infrastructure:
   ```bash
   source .venv/bin/activate
   aws sts get-caller-identity
   ```
   The command should return the account and principal that will run OpenTofu/CloudFormation.

4. Keep `.env` and any downloaded credentials out of source control. Prefer SSO or short-lived credentials for daily work; switch production workloads to IAM roles once they run on ECS/Lambda.

## Prerequisites

- AWS CLI v2 with credentials that can create IAM, VPC, ECS, DynamoDB, S3, and CloudFormation resources.
- Optional: [OpenTofu](https://opentofu.org/) v1.6.0+ if you plan to use the Terraform workflow.
- Docker (for building/pushing the `agenteval/api` container image referenced by the templates).
- S3 bucket to host nested CloudFormation templates (e.g. `agenteval-infra-templates`).

## Option 1: CloudFormation (Nested Stacks)

1. Package the nested templates and deploy the stack:

   ```bash
   scripts/deploy.sh \
     --mode cloudformation \
     --stack-name agenteval-staging \
     --environment staging \
     --region us-east-1 \
     --template-bucket agenteval-infra-templates
   ```

   The script will:
   - Sync the contents of `infrastructure/cloudformation/` to `s3://agenteval-infra-templates/cloudformation/agenteval/`.
    - Discover two available AZs in the target region and pass them to the nested stacks.
   - Deploy the root template (`main.yaml`) with IAM capabilities enabled.

2. After deployment, note the outputs:
   - `LoadBalancerDNSName` – public endpoint for the API.
   - `ResultsBucketName` / `ReportsBucketName` – S3 buckets for artifacts.
   - `EventBridgeBusArn` – bus for campaign lifecycle events.

3. Update your `.env` / application configuration with the infrastructure outputs.

To delete the stack:

```bash
aws cloudformation delete-stack --stack-name agenteval-staging --region us-east-1
```

## Option 2: OpenTofu / Terraform

1. Populate or override variables in `infrastructure/opentofu/terraform.tfvars.example` and copy it:

   ```bash
   cp infrastructure/opentofu/terraform.tfvars.example envs/staging.tfvars
   ```

   Edit `envs/staging.tfvars` with unique resource names (S3 buckets must be globally unique) and any overrides for Bedrock model IDs, replica regions, or tags. Example snippet:

   ```hcl
   aws_region              = "us-east-1"
   dynamodb_campaigns_table = "agenteval-staging-campaigns"
   s3_results_bucket       = "agenteval-staging-results-1234"
   eventbridge_bus_name    = "agenteval-staging"
   tags = {
     Project = "AgentEval"
     Environment = "staging"
   }
   ```

2. Initialize and review the stack:

   ```bash
   cd infrastructure/opentofu
   tofu init
   tofu fmt
   tofu validate
   tofu plan -var-file ../envs/staging.tfvars
   ```

   The plan output should show creation of the DynamoDB table, S3 bucket configuration (versioning + SSE), and EventBridge bus/archive. If you need remote state, configure an S3/DynamoDB backend before running `tofu init`.

3. Apply the plan:

   ```bash
   tofu apply -var-file ../envs/staging.tfvars
   ```

   Accept the prompt (or pass `--auto-approve`). Record the printed outputs—`dynamodb_table_arn`, `s3_results_bucket`, and `eventbridge_bus_arn`—and copy them into your `.env`/runtime configuration. When complete, return to the repo root.

4. Destroy the stack when finished:

   ```bash
   cd infrastructure/opentofu
   # Empty the S3 bucket first if force_destroy=false
   aws s3 rm s3://$(tofu output -raw s3_results_bucket) --recursive
   tofu destroy -var-file ../envs/staging.tfvars
   ```

   Ensure you clear object versions if versioning is enabled; otherwise `destroy` will fail.

## Option 3: Manual resource setup (Env + AWS CLI/bash)

Use this approach when you want to create just the core data/event dependencies without full IaC.

1. Export your admin profile so CLI commands run as the intended identity:

   ```bash
   export AWS_PROFILE=agenteval-admin
   export AWS_REGION=us-east-1
   ```

2. Create the DynamoDB campaigns table (adjust read/write capacity if you prefer provisioned mode):

   ```bash
   aws dynamodb create-table \
     --table-name agenteval-campaigns \
     --attribute-definitions AttributeName=PK,AttributeType=S AttributeName=SK,AttributeType=S \
     --key-schema AttributeName=PK,KeyType=HASH AttributeName=SK,KeyType=RANGE \
     --billing-mode PAY_PER_REQUEST \
     --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true \
     --stream-specification StreamEnabled=true,StreamViewType=NEW_AND_OLD_IMAGES \
     --tags Key=Project,Value=AgentEval
   ```

   Repeat for additional tables (`agenteval-turns`, `agenteval-evaluations`, `agenteval-attack-knowledge`) if your runtime requires them.

3. Provision the S3 results bucket with versioning and default encryption:

   ```bash
   BUCKET=agenteval-results-$(date +%s)
   aws s3api create-bucket --bucket "$BUCKET" --create-bucket-configuration LocationConstraint=$AWS_REGION
   aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
   aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration '
   {
     "Rules": [{
       "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "aws:kms"}
     }]
   }'
   aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
     BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
   ```

   Write the bucket name back to `.env` (`AWS_S3_RESULTS_BUCKET`). Create a separate reports bucket (`AWS_S3_REPORTS_BUCKET`) if you plan to store rendered reports.

4. Create the EventBridge bus and optional archive:

   ```bash
   aws events create-event-bus --name agenteval
   aws events create-archive \
     --name agenteval-archive \
     --event-source-arn arn:aws:events:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):event-bus/agenteval \
     --retention-days 90
   ```

5. Update `.env` with the resource names (tables, bucket, bus) and run `bash scripts/setup.sh` to ensure the Python environment is ready. Tests and local runs will now use the manually created infrastructure.

6. When cleaning up, delete the EventBridge archive/bus, empty and delete the S3 bucket, and remove each DynamoDB table:

   ```bash
   aws events delete-archive --name agenteval-archive
   aws events delete-event-bus --name agenteval
   aws s3 rm s3://$BUCKET --recursive
   aws s3api delete-bucket --bucket $BUCKET
   aws dynamodb delete-table --table-name agenteval-campaigns
   # repeat for other tables
   ```

## Container Image Expectations

Both IaC paths expect the AgentEval API image to be available in Amazon ECR (or an equivalent registry). Before deploying, build and push the image:

```bash
aws ecr create-repository --repository-name agenteval/api || true

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
IMAGE_TAG=${IMAGE_TAG:-latest}

aws ecr get-login-password --region "$REGION" | docker login \
  --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

docker build -t agenteval-api infrastructure/docker
docker tag agenteval-api "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/agenteval/api:$IMAGE_TAG"
docker push "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/agenteval/api:$IMAGE_TAG"
```

Update `ContainerImage` (CloudFormation) or `container_image` (OpenTofu) with the pushed URI.

## Post-Deployment Checklist

- Verify the load balancer DNS resolves and returns the API health endpoint (`/health`).
- Confirm ECS Service tasks are healthy in the AWS console.
- Check CloudWatch log groups `/aws/ecs/<env>/agenteval-api` and `/aws/ecs/<env>/otel-collector` for startup output.
- Ensure DynamoDB tables exist with point-in-time recovery enabled (campaigns, turns, evaluations, knowledge).
- Confirm S3 buckets enforce TLS and block public access.
- Publish a test event to EventBridge to validate permissions:

  ```bash
  aws events put-events \
    --region us-east-1 \
    --entries '[{"Source": "agenteval.demo", "DetailType": "smoke", "EventBusName": "agenteval-events", "Detail": "{\"message\": \"hello\"}"}]'
  ```

## Troubleshooting

- **Stack creation fails with IAM errors** – ensure your AWS credentials allow `iam:CreateRole`, `iam:AttachRolePolicy`, and `iam:PassRole`.
- **ALB health checks fail** – confirm the container image exposes the configured port (default `8000`) and implements `/health`.
- **Bucket name already in use** – update `results_bucket_name` / `reports_bucket_name` to globally unique values.
- **OpenTofu apply prompts for approval** – pass `--auto-approve` or answer `yes` when prompted.

For deeper insight into resources provisioned by either workflow, review the templates in `infrastructure/cloudformation/` or the modules in `infrastructure/opentofu/modules/`.
