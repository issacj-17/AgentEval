# Infrastructure Archive (Future Work)

The CloudFormation templates, deployment scripts, and Terraform/Docker placeholders were moved here
on 2025-10-22 to keep the active submission scope lightweight. The intent is to revisit these assets
post-hackathon to productionize the deployment story (ECS/Fargate, networking, IaC parity).

Artifacts preserved:

- `cloudformation/` – ECS cluster + network stack templates.
- `deploy.sh` & `DEPLOYMENT.md` – deployment workflow documentation.
- `docker/` and `terraform/` – empty scaffolds reserved for future implementation.

If we resume infrastructure work, restore this directory back to repo root or integrate into a
separate infra repository with appropriate CI/CD and environment guards.
