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

Run **both** the web app and the API. **Register / log in** on the site, then fill **Profile** with basic gym info (goals, equipment, etc.). Chat and profile data are stored **per user** in SQLite (`services/api/data/gymlife.db`); the coach only sees **your** messages and **your** profile when you’re logged in. Set `JWT_SECRET` in `services/api/.env` for real use (see `env.example`).

**LLM:** Defaults target **[Ollama](https://ollama.com)** locally (`env.example` → `.env`, then `ollama pull llama3.2` or change `OPENAI_MODEL`). For OpenAI’s cloud API instead, set `OPENAI_API_KEY` and adjust URLs/models as in `services/api/README.md`.

Optional: copy `apps/web/env.example` to `apps/web/.env.local` and set `NEXT_PUBLIC_API_URL` if the API is not on port 8000.

**Upgrading from an older build without auth:** delete `services/api/data/gymlife.db` once so the API can create the new `user` + `chat_message` schema.

The coach can **update the saved gym profile** when you ask in chat (via an LLM tool), as long as your model/API supports **function calling** (OpenAI; Ollama with a tool-capable model such as recent Llama 3).

## Repository

- **Remote:** [github.com/lujiahe2/GymLife](https://github.com/lujiahe2/GymLife)

---

*Next: RAG over your knowledge base and deployment.*
