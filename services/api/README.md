# GymLife — API (FastAPI)

RAG pipeline, embeddings, and agent endpoints will live here.

```bash
cd services/api
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- Health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Chat (coach)

- `POST /chat/messages` — body: `{ "session_id": "<uuid>", "content": "..." }` — saves user + assistant rows (assistant from Ollama / OpenAI per `.env`).
- `GET /chat/messages?session_id=<uuid>` — list messages for that session.
- `DELETE /chat/messages?session_id=<uuid>` — delete all messages for that session.

SQLite database file: `services/api/data/gymlife.db` (created on first request).

**Auth:** `POST /auth/register`, `POST /auth/login`, `GET /auth/me` (Bearer token).  
**Profile:** `GET /profile`, `PATCH /profile` (Bearer) — gym basics stored as JSON per user (`name`, `sex`, `age`, `height_cm`, `weight_kg`, `experience_level_index` 1–5, `goals`, etc.). `sex` must be one of: `female`, `male`, `non_binary`, `other`, `prefer_not_to_say`.  
**Calendar:** `GET /calendar/day?date=YYYY-MM-DD`, `PUT /calendar/day` (JSON body: `date`, `training_plan`, `diet_plan`), `GET /calendar/month?year=&month=` (returns `days_with_plans` for dots) — all Bearer, per user.  
**Chat:** requires `Authorization: Bearer <token>`; messages are scoped by `user_id` only. The coach may call **`update_gym_profile`** (profile JSON) and **`update_calendar_day`** (training/diet text for a `YYYY-MM-DD` date) when the user asks; updates are saved in the database (requires an LLM that supports tools, e.g. recent OpenAI models or Ollama models with tool support).

If you had an older DB from before auth, delete `services/api/data/gymlife.db` and restart the API so tables are recreated.

## LLM (Ollama by default)

Uses the **OpenAI-compatible** API that [Ollama](https://ollama.com) exposes at `http://127.0.0.1:11434/v1`.

1. Install Ollama, then run `ollama serve` (often automatic on macOS) and `ollama pull llama3.2` (or another model; match `OPENAI_MODEL` in `.env`).
2. Copy `env.example` to `.env` in this directory (defaults target Ollama).
3. Restart `uvicorn`.

If neither `OPENAI_API_KEY` nor `OPENAI_BASE_URL` is set, the assistant replies with setup instructions. With only `OPENAI_BASE_URL` set, the API uses the placeholder key `ollama` (Ollama ignores it).

**OpenAI cloud:** Put your real `OPENAI_API_KEY` in `.env`, set `OPENAI_MODEL` (e.g. `gpt-4o-mini`), and either remove `OPENAI_BASE_URL` or set it to `https://api.openai.com/v1`.

### If the model never replies

1. **Ollama running:** `curl http://127.0.0.1:11434/api/tags` should return JSON.
2. **Model name:** Run `ollama list` and set `OPENAI_MODEL` to an exact tag (try `llama3.2:latest` if `llama3.2` fails).
3. **Wait:** First generation after a pull can take **30–60+ seconds** on CPU; the chat UI shows “Coach is thinking…”.
4. **Restart the API** after editing `services/api/.env` (settings load at process start). `.env` is always read from `services/api/.env`, even if you start uvicorn from another directory.
