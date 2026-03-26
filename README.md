# GymLife

A web app that helps gym beginners build and follow training plans, with **RAG** (retrieval-augmented generation) for personalized guidance and **gamification** (streaks, progress, unlocks) inspired by apps like Duolingo, in a workout experience similar in spirit to Ladder.

## Monorepo layout

```
GymLife/
├── apps/web/              # Next.js (TypeScript) — UI + BFF
├── services/api/          # FastAPI — RAG, embeddings, agent HTTP/SSE
├── packages/shared/       # Optional shared TS types (wire up later)
├── data/knowledge-base/   # Source docs for ingestion into the vector store
├── infra/aws/             # AWS: IaC placeholders (CDK/Terraform/SAM)
├── docker-compose.yml     # Local Postgres + pgvector
└── README.md
```

| Part | Role |
|------|------|
| **apps/web** | React UI, workout flows, streaks; calls the API for chat/RAG. |
| **services/api** | Python service: retrieval, LLM orchestration, streaming responses. |
| **data/knowledge-base** | Curated fitness content for your RAG index (you control what ships). |
| **docker-compose** | Dev database with **pgvector** for embeddings. |
| **infra/aws** | Placeholder for AWS deployment (see `infra/aws/README.md`, `env.example`). |

## Quick start

**Database (optional, for Postgres + pgvector):**

```bash
docker compose up -d
```

**Web app:**

```bash
cd apps/web && npm install && npm run dev
```

→ [http://localhost:3000](http://localhost:3000)

**API:**

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

→ [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Repository

- **Remote:** [github.com/lujiahe2/GymLife](https://github.com/lujiahe2/GymLife)

---

*Next: env files (`.env.example`), auth, and RAG routes on the API.*
