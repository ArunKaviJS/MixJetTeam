# MixJet — Email → AI → Awery ERP

Three independent parts:

| Folder | What | Stack | Port |
|---|---|---|---|
| [`ai/`](ai/) | Gmail listener → LLM field extraction → merged PDF to S3 → MongoDB | Python (script) | — |
| [`awery-backend/`](awery-backend/) | Serves the file queue + pushes extracted data to Awery ERP | Python / FastAPI | 8200 |
| [`frontend/`](frontend/) | Light aviation-themed UI: queue + review + "Proceed → Awery" | React / Vite | 5173 |

```
Gmail ──▶ ai/ ──▶ MongoDB (tb_file_details) ──▶ awery-backend ──▶ Awery ERP
                                        ▲                │
                                        └──── frontend ──┘  (list, edit, Proceed)
```

`ai/` and `awery-backend` share the same MongoDB collection — that's the only link
between them. See [`awery-backend/HOW_IT_WORKS.md`](awery-backend/HOW_IT_WORKS.md)
for the field-by-field mapping and what Proceed stores.

## Run the whole thing (3 terminals)

```bash
# 1 — AI listener (you already know this part)
cd ai && venv\Scripts\activate && python main.py

# 2 — Awery backend
cd awery-backend && venv\Scripts\activate && python run.py      # http://localhost:8200/docs

# 3 — Frontend
cd frontend && npm run dev                                      # http://localhost:5173
```

Flow: send a "Permit Request" email → `ai/` processes it and writes a Mongo doc →
it appears in the frontend within ~15 s → open it, review the fields → **Proceed →**
creates the flight in Awery and shows the `flight_id`.

## First-time setup

Each folder has its own `.env` (all git-ignored) and its own `README.md`:

- `ai/.env` — IMAP, Azure OpenAI, AWS, Mongo (unchanged from before).
- `awery-backend/.env` — copy from `.env.example`, set `AWERY_ERP_API_BEARER_TOKEN`
  and `MONGO_URI`.
- `frontend/.env` — copy from `.env.example` (`VITE_API_BASE=http://localhost:8200`).

```bash
cd awery-backend && python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
cd ../frontend && npm install
```

## Testing with Postman

`awery-backend/postman/` has two collections — one for this backend, one for calling
Awery's `/rpc/json/` directly. Steps in [`awery-backend/README.md`](awery-backend/README.md).
Known-good sample: `flight_no = MIX22985` exists in the Awery dev instance.
