# Environment Variables

All variables live in `.env` at the repo root (copy from `.env.example`).
Both `docker-compose.yml` and the backend's `pydantic-settings` config read
from it. Frontend build-time variables (`NEXT_PUBLIC_*`) must additionally be
passed as Docker build args (see `infra/docker-compose.yml`), since Next.js
inlines them at build time, not runtime.

| Variable | Default | Used by | Notes |
|---|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://medirag:medirag@localhost:5432/medirag` | backend | For local dev without Docker/Postgres, `sqlite:///./dev.db` works (see `db_types.py`'s dialect fallback). Hosted Postgres providers (Render, Railway, Neon, ...) hand out a plain `postgresql://` URL -- `app/db.py` auto-upgrades that scheme to `postgresql+psycopg://` (only psycopg v3 is installed, not psycopg2), so either form works as-is. |
| `LLM_PROVIDER` | `mock` | backend | `mock`, `anthropic`, `gemini`, or `ollama`. `gemini` doesn't mean "Gemini only" -- with at least `GEMINI_API_KEY` set, it builds the full `CascadingLLMProvider` chain (Gemini -> Groq -> Ollama locally; Gemini -> Groq only in production, see [DEPLOYMENT.md](DEPLOYMENT.md)), skipping to the next provider on failure or a vague answer. |
| `OCR_PROVIDER` | `mock` | backend | `mock` or `tesseract` (requires the Tesseract binary installed locally). |
| `MAPS_PROVIDER` | `mock` | backend | Only `mock` is implemented; the interface (`ProviderDirectory`) is ready for a real Places-style adapter. |
| `ANTHROPIC_API_KEY` | *(empty)* | backend | Required only when `LLM_PROVIDER=anthropic`. |
| `GEMINI_API_KEY` | *(empty)* | backend | 1st in the cascade when `LLM_PROVIDER=gemini`. Get one from [Google AI Studio](https://aistudio.google.com/apikey). Free tier is 20 requests/day. |
| `GEMINI_MODEL` | `gemini-3.6-flash` | backend | Only used when `LLM_PROVIDER=gemini`. |
| `GROQ_API_KEY` | *(empty)* | backend | 2nd in the cascade, tried automatically if Gemini fails or produces an unsupported/vague answer -- not a separate `LLM_PROVIDER` value of its own. Free key from [console.groq.com](https://console.groq.com). |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | backend | Only used as part of the Gemini cascade. |
| `OLLAMA_HOST` | `http://localhost:11434` | backend | 3rd in the cascade, and used directly when `LLM_PROVIDER=ollama`. No API key -- requires [Ollama](https://ollama.com) installed and running locally, with the model already pulled. Not available in this app's current production deployment (needs a persistent GPU/CPU box). |
| `OLLAMA_MODEL` | `llama3.1:8b` | backend | Only used when `LLM_PROVIDER=ollama` or as the cascade's 3rd step. Must match a model you've run `ollama pull <model>` for. A smaller/faster model (`llama3.2:3b`) was tested and rejected for this role -- it fabricated medical content with a real-but-unrelated citation attached; see [DECISIONS.md](DECISIONS.md). |
| `AUTH_SECRET` | `change-me-in-production` | backend | JWT signing secret. **Must** be changed and kept secret in any real deployment. Render's blueprint (`render.yaml`) auto-generates a real one; nothing to set by hand there. |
| `AUTH_TOKEN_TTL_MINUTES` | `60` | backend | Session length. |
| `STORAGE_DIR` | `./uploads` | backend | Local filesystem storage root for uploads (prescription/medicine images). Not yet wired to an S3-compatible adapter; ephemeral on Render's free tier (doesn't survive a redeploy). |
| `APP_URL` | `http://localhost:3000` | backend | Used for CORS `allow_origins` -- exactly one origin, no list. In production this must be the real deployed frontend URL (e.g. the Vercel domain), or the browser will block every request with a CORS error. |
| `API_URL` | `http://localhost:8000` | backend | Informational; not read by the frontend (see `NEXT_PUBLIC_API_URL` below). |
| `DEFAULT_REGION` | `US` | backend | Fallback region for `/api/emergency-information` when none is specified. |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | frontend (build-time) | The browser's fetch target. Must be reachable from the *user's* machine, not just from inside a Docker network -- this is why `docker-compose.yml` sets it to `http://localhost:8000`, not `http://api:8000`. Baked in at build time, so a Vercel deployment needs it set (`vercel env add NEXT_PUBLIC_API_URL production`) *before* the first production build, not after. |

## Never commit

`.env` is gitignored. Never commit real values for `ANTHROPIC_API_KEY`,
`GEMINI_API_KEY`, `GROQ_API_KEY`, `AUTH_SECRET`, `DATABASE_URL` (once it
contains real hosted-database credentials), or any future maps/OCR API key.
`.env.example` must only ever contain placeholders -- diff it against `.env`
before committing either file if you're ever unsure which one you're
looking at.
