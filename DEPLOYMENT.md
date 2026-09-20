# Deploying MediRAG

Two pieces, deployed separately: the FastAPI backend (Render) and the
Next.js frontend (Vercel). Ollama is dropped in production -- it needs a
persistent GPU/CPU box, not a serverless/PaaS host -- so the deployed
cascade is effectively Gemini -> Groq, still validated the same way.

## 1. Push this repo to GitHub

Render's Blueprint deploy and Vercel's dashboard both deploy from a git
remote (the Vercel CLI can also deploy from local disk, but GitHub gives
you auto-redeploy on push, which is worth having).

```bash
# create an empty repo on GitHub first (github.com/new), then:
git remote add origin <your-repo-url>
git push -u origin main
```

## 2. Backend: Render

`render.yaml` at the repo root already defines the web service (built from
`services/api/Dockerfile`) and a free Postgres database together.

1. On [render.com](https://render.com), **New > Blueprint**, point it at
   this GitHub repo. Render reads `render.yaml` and provisions both
   resources.
2. It will prompt for the env vars marked `sync: false` -- set:
   - `GEMINI_API_KEY`, `GROQ_API_KEY` -- your existing keys.
   - `APP_URL` -- leave a placeholder for now (e.g. `https://example.com`);
     you'll update it once Vercel gives you the real frontend URL, since
     it's only used for CORS.
3. Deploy. `alembic upgrade head` runs automatically on container start
   (see `services/api/Dockerfile`), so the schema is ready immediately.
4. **One-time only**, seed demo data and ingest the real reference corpus
   via Render's **Shell** tab on the web service:
   ```bash
   python -m scripts.seed
   python -m scripts.ingest_real_sources
   ```
5. Note the service URL Render gives you (`https://medirag-api-xxxx.onrender.com`)
   -- that's `NEXT_PUBLIC_API_URL` for the frontend.

Free-tier Postgres on Render expires after 90 days; free web services spin
down after 15 minutes idle (first request after that takes a few seconds
to wake up). Fine for a demo, not for real traffic.

## 3. Frontend: Vercel

```bash
cd apps/web
vercel link        # first time: creates/links the Vercel project
vercel env add NEXT_PUBLIC_API_URL production   # paste the Render URL from step 2.5
vercel --prod
```

`NEXT_PUBLIC_API_URL` is baked in at build time, so it must be set before
the first `--prod` deploy (or you redeploy after adding it).

## 4. Close the loop: CORS

Back on Render, update `APP_URL` to the real Vercel domain Vercel just gave
you, and let it redeploy (Render restarts automatically on env var change).
Without this, the deployed frontend's requests will be blocked by CORS.

## Known gaps in this deployment (vs. local dev)

- **No Ollama fallback.** If both Gemini and Groq fail (quota, outage), the
  cascade's last step will fail to connect and the response abstains
  ("Sorry, this question is new to me...") instead of falling through to a
  local model -- same safe behavior as any other real failure, just with
  one less fallback layer.
- **Ephemeral file storage.** Uploaded files (`STORAGE_DIR`) don't survive
  a redeploy on Render's free tier -- fine given prescription/medicine
  scan upload UI is currently gated behind "Coming Soon" anyway.
