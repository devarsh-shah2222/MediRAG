# Environment Variables

All variables live in `.env` at the repo root (copy from `.env.example`).
Both `docker-compose.yml` and the backend's `pydantic-settings` config read
from it. Frontend build-time variables (`NEXT_PUBLIC_*`) must additionally be
passed as Docker build args (see `infra/docker-compose.yml`), since Next.js
inlines them at build time, not runtime.

| Variable | Default | Used by | Notes |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://medirag:medirag@localhost:5432/medirag` | backend | For local dev without Docker/Postgres, `sqlite:///./dev.db` works (see `db_types.py`'s dialect fallback). |
| `LLM_PROVIDER` | `mock` | backend | `mock`, `anthropic`, `gemini`, or `ollama`. |
| `OCR_PROVIDER` | `mock` | backend | `mock` or `tesseract` (requires the Tesseract binary installed locally). |
| `MAPS_PROVIDER` | `mock` | backend | Only `mock` is implemented; the interface (`ProviderDirectory`) is ready for a real Places-style adapter. |
| `ANTHROPIC_API_KEY` | *(empty)* | backend | Required only when `LLM_PROVIDER=anthropic`. |
| `GEMINI_API_KEY` | *(empty)* | backend | Required only when `LLM_PROVIDER=gemini`. Get one from [Google AI Studio](https://aistudio.google.com/apikey). |
| `GEMINI_MODEL` | `gemini-3.6-flash` | backend | Only used when `LLM_PROVIDER=gemini`. |
| `OLLAMA_HOST` | `http://localhost:11434` | backend | Only used when `LLM_PROVIDER=ollama`. No API key -- requires [Ollama](https://ollama.com) installed and running locally, with the model already pulled. |
| `OLLAMA_MODEL` | `llama3.1` | backend | Only used when `LLM_PROVIDER=ollama`. Must match a model you've run `ollama pull <model>` for. |
| `AUTH_SECRET` | `change-me-in-production` | backend | JWT signing secret. **Must** be changed and kept secret in any real deployment. |
| `AUTH_TOKEN_TTL_MINUTES` | `60` | backend | Session length. |
| `STORAGE_DIR` | `./uploads` | backend | Local filesystem storage root for uploads (prescription/medicine images). Not yet wired to an S3-compatible adapter. |
| `APP_URL` | `http://localhost:3000` | backend | Used for CORS `allow_origins`. |
| `API_URL` | `http://localhost:8000` | backend | Informational; not read by the frontend (see `NEXT_PUBLIC_API_URL` below). |
| `DEFAULT_REGION` | `US` | backend | Fallback region for `/api/emergency-information` when none is specified. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | frontend (build-time) | The browser's fetch target. Must be reachable from the *user's* machine, not just from inside a Docker network -- this is why `docker-compose.yml` sets it to `http://localhost:8000`, not `http://api:8000`. |

## Never commit

`.env` is gitignored. Never commit real values for `ANTHROPIC_API_KEY`,
`AUTH_SECRET`, or any future maps/OCR API key.
