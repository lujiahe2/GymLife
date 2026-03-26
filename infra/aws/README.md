# AWS — infrastructure (placeholder)

Use this folder for **Infrastructure as Code** and AWS-oriented config when you deploy GymLife.

## Suggested layout (add as you choose)

| Path | Typical use |
|------|-------------|
| `cdk/` | AWS CDK (TypeScript or Python) stacks: VPC, ECS/Fargate, RDS, ALB, etc. |
| `terraform/` | Terraform modules and `*.tf` for the same resources. |
| `sam/` | AWS SAM if you prefer Lambda + API Gateway for parts of the API. |

You can start with one tool (CDK or Terraform); keep app code in `apps/` and `services/` and only put **cloud definitions** here.

## Services you may wire up later

- **App hosting:** ECS on Fargate, App Runner, or Amplify (frontend-only) + separate API.
- **Database:** RDS PostgreSQL with `pgvector`, or Aurora.
- **Secrets:** AWS Secrets Manager or SSM Parameter Store.
- **RAG / LLM:** Amazon Bedrock; embeddings in OpenSearch Serverless or a managed vector store.
- **Object storage:** S3 for uploads and knowledge-base artifacts.
- **CI/CD:** CodePipeline, GitHub Actions → ECR/ECS (OIDC to AWS).

## Environment variables

Copy `env.example` to a **local** untracked file (for example `.env.aws` in this directory) and fill values. Do **not** commit real keys or ARNs.

See `env.example` for placeholder names only.
