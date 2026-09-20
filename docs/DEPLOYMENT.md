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
3. Deploy. On every container start, `services/api/Dockerfile`'s CMD runs
   `alembic upgrade head`, then `scripts.seed`, then `scripts.ingest_real_sources`
   (best-effort -- see below), then starts uvicorn. No manual Shell step
   needed: both scripts are idempotent (existence/content-hash checked), so
   re-running them on every boot is safe and the schema + reference content
   are ready as soon as the deploy finishes.
   - `ingest_real_sources` makes live calls to openFDA/MedlinePlus with no
     retry logic, so it's wrapped in `|| true` -- a transient fetch failure
     there can't block the API from starting. If you ever suspect it failed
     (chat abstains on everything with no evidence), check the deploy's
     boot log for `Ingested '...'` lines, or re-run it once by hand from
     your own machine against Render's **External Database URL** (Postgres
     service -> **Info** tab) -- `DATABASE_URL=<that url> python -m
     scripts.ingest_real_sources` from `services/api` with your `.venv`
     active. It's safe to re-run; it only adds/updates content, never
     deletes.
4. Note the service URL Render gives you (`https://<service-name>.onrender.com`,
   e.g. `https://medirag-api.onrender.com`) -- that's `NEXT_PUBLIC_API_URL`
   for the frontend.

Free-tier Postgres on Render expires after 90 days; free web services spin
down after 15 minutes idle (first request after that takes a few seconds
to wake up). Fine for a demo, not for real traffic.

## 3. Frontend: Vercel

```bash
cd apps/web
vercel link        # first time: creates/links the Vercel project
vercel env add NEXT_PUBLIC_API_URL production   # paste the Render URL from step 2.4
vercel --prod
```

`NEXT_PUBLIC_API_URL` is baked in at build time, so it must be set before
the first `--prod` deploy (or you redeploy after adding it).

**Set Root Directory to `apps/web`, even though `vercel --prod` above works
without it.** This is a monorepo, and Vercel's Root Directory project
setting defaults to the repo root. Running `vercel --prod` from inside
`apps/web` happens to work anyway (the CLI only uploads the current
directory), which masks the misconfiguration completely -- but if you ever
connect this repo to Vercel's GitHub integration for auto-deploy-on-push
(Vercel may offer to do this automatically once it sees a git remote),
those builds clone the *whole* repo and use the Root Directory setting for
real, failing with "Couldn't find any `pages` or `app` directory" since
Next.js actually lives in `apps/web`, not the repo root. Fix once, in
**Project Settings -> General -> Root Directory -> `apps/web`** -- there's
no CLI command or `vercel.json` key for this, it's dashboard/API-only.

**Optional: a cleaner `.vercel.app` domain.** Vercel auto-generates one from
the project name, which can come out looking unrelated to the project (e.g.
`web-<hash>.vercel.app` for a project named after its directory, `web`).
Claim a better one with `vercel domains add <name>.vercel.app` (not
`vercel alias set`, which creates an alias that doesn't inherit the
project's deployment-protection settings correctly and can end up behind an
unexpected Vercel SSO wall) -- names are first-come-first-served across all
of Vercel, so try a few if your first choice is taken.

## 4. Close the loop: CORS

Back on Render, update `APP_URL` to the real Vercel domain Vercel just gave
you, and let it redeploy (Render restarts automatically on env var change).
Without this, the deployed frontend's requests will be blocked by CORS.

## Known gaps in this deployment (vs. local dev)

- **No Ollama fallback, and free-tier quotas make this more visible than
  you'd expect.** If both Gemini and Groq fail, the cascade's last step
  can't connect and the response abstains ("Sorry, this question is new to
  me...") instead of falling through to a local model -- same safe behavior
  as any other real failure, just with one less fallback layer. Gemini's
  free tier is only 20 requests/day, so it's live-verified to run out from
  ordinary testing alone; Groq then does double duty and can hit its own
  rate limits under the same heavy testing. In real usage spread across a
  day this is rare -- it only showed up here because of rapid repeated
  testing during setup, not because the cascade is unreliable.
- **Ephemeral file storage.** Uploaded files (`STORAGE_DIR`) don't survive
  a redeploy on Render's free tier -- fine given prescription/medicine
  scan upload UI is currently gated behind "Coming Soon" anyway.
