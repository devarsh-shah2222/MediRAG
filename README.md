# MediRAG

Evidence-grounded AI healthcare information and care navigation assistant.

MediRAG helps people understand healthcare and medication information in plain
language, using retrieval-augmented generation over a curated reference
library, with a rule-based safety layer that recognizes when a situation may
need urgent professional attention. It is **not** a diagnostic tool, does not
prescribe, and never tells a user to start, stop, or change a medication.

This is a core-first MVP: chat + RAG + evidence/citations + safety triage +
medication info are implemented deeply and tested. Other features (scanner,
prescription explainer, doctor finder, multilingual UI, admin) are functional
but thinner slices. See [DECISIONS.md](DECISIONS.md) for what was
deliberately simplified and why, and the **Known limitations** section below
for what's out of scope for this pass.

## Stack

- **Frontend**: Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL + pgvector (single database, no separate vector DB service)
- **LLM / OCR / Maps**: pluggable provider interfaces, defaulting to deterministic
  mock implementations so the whole app runs with zero external API keys

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full picture and
[RAG_ARCHITECTURE.md](RAG_ARCHITECTURE.md) / [SAFETY.md](SAFETY.md) for the two
most safety-critical subsystems.

## Run locally with Docker

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

Then seed demo providers/settings, and ingest the real reference library
(one-time, or whenever you want to refresh it with the latest source data):

```bash
docker compose -f infra/docker-compose.yml exec api python -m scripts.seed
docker compose -f infra/docker-compose.yml exec api python -m scripts.ingest_real_sources
```

The second command fetches real content live from openFDA (drug labels) and
MedlinePlus (NIH health topics) -- see [RAG_ARCHITECTURE.md](RAG_ARCHITECTURE.md#real-reference-content)
for what it ingests and why those two sources.

- Web: http://localhost:3000
- API: http://localhost:8000 (docs at `/docs`)

## Run locally without Docker

Backend:

```bash
cd services/api
python -m venv .venv
.venv/Scripts/activate   # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
# Postgres+pgvector required for production use; for local dev without Docker,
# point DATABASE_URL at sqlite:///./dev.db instead -- see ENVIRONMENT.md.
alembic upgrade head      # only when using Postgres; sqlite dev falls back to create_all via the seed script
python -m scripts.seed
python -m scripts.ingest_real_sources   # fetches real content from openFDA + MedlinePlus
uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Tests

```bash
# Backend: 98 unit + integration tests, run against SQLite, no Docker needed
cd services/api && pytest -q

# Frontend: component tests
cd apps/web && npm test

# Frontend: end-to-end (requires both dev servers running)
cd apps/web && npx playwright install chromium && npx playwright test

# RAG / safety evaluation suite (fetches real content live -- needs internet)
python -m evals.run
```

## Reference content

The RAG corpus is real content, not fabricated or hand-authored text: **openFDA**
(U.S. FDA structured drug labels) for seven medications, and **MedlinePlus**
(NIH/National Library of Medicine consumer health summaries) for the four
health topics. Both are public-domain U.S. government works, fetched live by
`scripts/ingest_real_sources.py` (not scraped from arbitrary sites). See
[RAG_ARCHITECTURE.md](RAG_ARCHITECTURE.md#real-reference-content) for the
ingestion pipeline, what content is deliberately excluded (dosage/frequency
text), and known content-quality caveats of automated real-source ingestion.

**India-specific coverage**: there is no Indian equivalent of openFDA reachable
as a public API -- CDSCO (India's drug regulator) publishes only static
approved-drug-name lists, not structured label content. Rather than scrape a
commercial pharmacy site and present it as authoritative, India-relevant
coverage means: four more medicines heavily prescribed in India (metformin,
amlodipine, azithromycin, cetirizine) via the same real openFDA pipeline, plus
verified-real Indian brand names (Crocin, Dolo, Calpol, Brufen, Novamox,
Glycomet, Amlong, Amlopres, Azithral, Alerid) wired in as query synonyms, so
asking about a brand name retrieves the right generic-name content. See
[DECISIONS.md](DECISIONS.md) for the research behind this and what a future,
more India-specific source would need.

## Known limitations (deferred, tracked)

- **Mock providers by default; a real 3-provider chain when `LLM_PROVIDER=gemini`.**
  LLM, OCR, and maps/provider-directory all default to deterministic mock
  implementations (see `LLM_PROVIDER`, `OCR_PROVIDER`, `MAPS_PROVIDER` in
  `.env.example`). With `LLM_PROVIDER=gemini` and at least a `GEMINI_API_KEY`
  configured, the app tries **Gemini -> Groq -> Ollama** in order,
  automatically moving to the next provider when one either raises (network
  error, API outage, rate limit, timeout) or produces an answer the citation
  validator would abstain on (unsupported/vague) -- see
  `CascadingLLMProvider` in `providers/llm.py` and `DECISIONS.md`. Every
  candidate answer is checked against the *same* retrieved evidence with the
  *same* validator regardless of which provider produced it, so cascading
  can only ever surface a better-grounded answer or fall through to the same
  abstention a single provider would have produced -- never a less-grounded
  one slipping through. `LLM_PROVIDER=anthropic` and `LLM_PROVIDER=ollama`
  (standalone, no key or internet access needed, but requires
  [Ollama](https://ollama.com) installed locally with a model pulled) remain
  available as direct single-provider choices outside that chain.
  **Live-verified with a real failure, not a simulated one**: while testing,
  Gemini's free-tier daily quota (20 requests) genuinely ran out mid-session,
  producing a real `429 RESOURCE_EXHAUSTED` error; the chain caught it and
  Groq answered correctly in under 3 seconds, without ever needing to reach
  the much slower Ollama step. Ollama itself is also live-verified: installed
  via winget, tested end-to-end with `llama3.1:8b` (4.9 GB, 16 GB RAM, no
  GPU) -- correct and grounded, but **3m38s** for one response on CPU-only
  inference, versus 2-5s for Gemini/Groq/Anthropic. `llama3.2:3b` (2 GB,
  ~5s) was tried as a faster alternative and rejected: tested live in the
  same failure scenario, it fabricated medical content and attached a real
  but unrelated citation to it, an error the validator only caught by
  accident (see `RAG_ARCHITECTURE.md`'s claim-validation section). The
  emergency safety path is unaffected by any of this either way -- it
  short-circuits before reaching any LLM (confirmed live at ~0.08s
  regardless of provider or quota state), so a slow or unavailable model
  never delays urgent-care guidance. OCR and maps remain mock-only; those
  interfaces are ready for a real implementation but none is wired up.
- **Non-Latin-script retrieval is weak.** The mock embedding provider only
  tokenizes ASCII word characters, so a query typed entirely in Hindi/Gujarati
  script will usually retrieve no evidence and abstain, even though the UI
  and API correctly handle the language end-to-end. A real embedding model
  fixes this; see [DECISIONS.md](DECISIONS.md).
- **No real map tiles** on the Doctors page; it's list-first with a "get
  directions" link out to OpenStreetMap.
- **No exhaustive security/accessibility/load-test suites.** Core safety and
  auth paths are tested; a full WCAG automated gate, penetration-style
  security tests, and load testing are not implemented.
- Only 6 of the 15 documents from the original spec exist
  (README, ARCHITECTURE, SAFETY, RAG_ARCHITECTURE, DECISIONS, ENVIRONMENT).
  PRODUCT_SPEC, UX_GUIDELINES, SECURITY, THREAT_MODEL, API, DATABASE, TESTING,
  EVALUATION, DEPLOYMENT are not written.
