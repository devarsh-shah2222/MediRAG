# Decisions

Architectural and scoping decisions, in the order they came up, with the
reasoning and the condition that would justify revisiting them.

## Real reference content: openFDA + MedlinePlus, not hand-authored demo text

**Decision**: replaced the original hand-authored demo reference library with
content fetched live from openFDA (drug labels) and MedlinePlus (health
topics) -- see `scripts/ingest_real_sources.py` and
[RAG_ARCHITECTURE.md](RAG_ARCHITECTURE.md#real-reference-content).
**Why**: the demo docs were accurate in substance but written by an AI
assistant, not sourced from an authoritative reference -- fine for proving
the RAG/citation/safety architecture works, but not something a user should
be shown as if it were real medical guidance. openFDA and MedlinePlus are
both public domain U.S. government works, structured enough to parse
reliably, and don't raise the "scraping an arbitrary site" concern the spec
explicitly warns against.
**Cost of the switch**: real content is messier than hand-written demo copy
(see RAG_ARCHITECTURE.md's content-quality caveats), and it exposed three
real retrieval bugs that the cleaner demo text had never triggered (a
missing paracetamol/acetaminophen synonym, a document-collision case from
term-frequency blindness, and a rare-word-gating false positive) -- each
fixed and pinned down with a regression test, not papered over.
**Revisit when**: more topics/medications are needed than fit comfortably in
one script (see the script's own ponytail note), or a jurisdiction outside
the U.S. needs region-specific sources (e.g. UK's NHS/MHRA, India's CDSCO).

## India-specific coverage: more openFDA medicines + brand-name synonyms, not a scraped source

**Decision**: when asked to add Indian medicine data, researched real options
first (CDSCO, India's National Health Portal, data.gov.in) rather than
scraping a commercial pharmacy site (1mg/Netmeds/PharmEasy-style) and
presenting it as authoritative. Findings: CDSCO publishes only static
approved-drug-name lists, no structured label content via API; India's
National Health Portal (nhp.gov.in) is a web portal, not an API, and was
also unreachable as a live TCP connection from the build sandbox (DNS
resolves, the connection itself times out -- an environment restriction, not
evidence the site is down) so it couldn't be verified either way; data.gov.in's
medicine datasets sit behind a JS-rendered SPA that needs a registered API
key. None of these are usable the way openFDA is.
**What was built instead**: four more medicines heavily prescribed in India
(metformin, amlodipine, azithromycin, cetirizine) via the same real openFDA
pipeline -- the pharmacology is the same regardless of country even though
the label itself is FDA-sourced -- plus ten verified-real Indian brand names
(checked via web search, not recalled from memory alone: Crocin/Dolo/Calpol
for paracetamol, Brufen for ibuprofen, Novamox for amoxicillin, Glycomet for
metformin, Amlong/Amlopres for amlodipine, Azithral for azithromycin, Alerid
for cetirizine) wired in as query-time synonyms
(`providers/stopwords.py`'s `_SYNONYM_CANONICAL`), the same mechanism already
built for paracetamol/acetaminophen.
**What this is NOT**: real Indian regulatory content (CDSCO approval status,
India-specific dosing conventions, Ayurvedic/traditional medicine
information). It's the same real FDA pharmacological content, made
discoverable by the names an Indian user is more likely to actually type.
**Revisit when**: a real, structured, publicly-callable Indian source becomes
available or reachable, or the user has a specific dataset/API in mind for
that purpose.

## Ollama as a fourth LLM provider, grounded the same way as the others

**Decision**: added `OllamaProvider` behind the same `LLMProvider` interface
as Mock/Anthropic/Gemini, using the identical evidence-only system prompt and
citation-marker contract -- not an unrestricted general-purpose chatbot mode.
**Why**: the request was for "an offline model that can answer any type of
question," which could be read two ways: (a) a fourth real-generation
backend with no API key/internet dependency, or (b) a chat mode that bypasses
RAG grounding and safety constraints entirely. (b) would undo the core
architectural guarantee this app is built around -- every factual medical
claim must trace to retrieved, cited evidence, enforced by `claims.py`
regardless of which model answers. (a) is a legitimate, low-risk addition
that fits the existing provider-interface pattern exactly. Built (a);
flagged the interpretation choice explicitly so it can be corrected if (b)
was actually wanted.
**Live-verified**: with explicit user confirmation (installing software and a
multi-GB download both cross this project's "ask first" line), installed
Ollama via winget and pulled `llama3.1:8b` (4.9 GB) on the build machine
(16 GB RAM, no GPU). A real grounded chat query produced a correct, cited
answer using the actual retrieved evidence -- the citation-marker format the
model produced needed no parser changes, unlike Gemini's two format quirks.
**Real cost measured, not estimated**: one chat response took 3m38s on
CPU-only inference, versus 2-5s for Gemini/Anthropic. This is the genuine
offline/free-vs-fast tradeoff, not a bug -- a GPU or a smaller model
(`llama3.2:3b` et al.) would trade answer quality for latency. Confirmed the
emergency safety path is unaffected (0.12s, since it short-circuits before
reaching any LLM regardless of provider) -- a slow local model can never
delay urgent-care guidance.
**Revisit when**: latency is unacceptable for the target hardware (switch to
a smaller model or add a loading/progress state in the UI for the ollama
path specifically), or a GPU becomes available to test against.

## Gemini primary + automatic Ollama fallback (superseded below), and why the fallback model isn't the small one

**Superseded by** "Gemini -> Groq -> Ollama cascade" below, which adds Groq
as a second real provider and generalizes the two-provider fallback into an
N-provider chain. Kept here because the model-choice reasoning still applies
unchanged to Ollama's position as the last link in that chain.
**Decision**: `FallbackLLMProvider` wraps Gemini (primary) and Ollama
(fallback): if a Gemini call raises -- network error, API outage, rate
limit, timeout -- the app automatically retries with the local Ollama model
and returns that answer, so the user gets a real response instead of a
generic error. This only triggers on an actual exception from the primary
call, never on a normal abstention (`claims.py` correctly declining to
answer because the evidence didn't support one is not a failure to recover
from -- see `providers/llm.py`'s `FallbackLLMProvider` docstring).
**Why the fallback model is `llama3.1:8b`, not the requested `llama3.2:3b`**:
tested both live, in the actual failure scenario (a broken Gemini key
forcing a real fallback), on the same real question. `llama3.2:3b` answered
in ~5s but fabricated medical content -- it claimed amoxicillin treats
"sexually transmitted infections such as chlamydia and gonorrhea," which
appears nowhere in the retrieved evidence, and attached a real, retrieved
chunk id to that sentence whose actual content was an unrelated brand-name
note. `claims.py` currently only checks that a cited id exists in the
retrieved set, not that its content actually supports the claim (see
RAG_ARCHITECTURE.md's known-limitations note on this), so a real-but-wrong
citation like this would normally pass validation; it was only caught here
because the same response also used the wrong marker syntax
(`[chunk_id: X]` instead of `[[cite:X]]`). `llama3.1:8b`, tested the same
way, produced a correctly-formatted, fully-grounded, correctly-abstaining
answer with no fabrication. A fallback's entire job is to be trustworthy
when the primary is already down; a fast fallback that sometimes fabricates
medical claims is worse than a slow one that doesn't. `llama3.2:3b` remains
pulled and available (`OLLAMA_MODEL=llama3.2:3b`) for anyone who wants to
use Ollama directly and accepts that tradeoff knowingly.
**Revisit when**: `claims.py` gets real entailment checking (making a small
model's citation mistakes structurally harmless rather than just usually
caught), or a different small model is evaluated the same way and found
reliable.

## Gemini -> Groq -> Ollama cascade, escalating on vague answers too

**Decision**: replaced the two-provider `FallbackLLMProvider` with
`CascadingLLMProvider`, an ordered list of providers tried in sequence.
Default chain when `LLM_PROVIDER=gemini`: Gemini, then Groq (added this
round, a free hosted-inference API for open models), then Ollama. A
provider is skipped to the next one when it either raises an exception
(as before) **or** succeeds but produces an answer `claims.py` would
abstain on (no supported sentences, or too many unsupported ones) --
explicitly requested (previously this codebase's stance, recorded in the
now-superseded entry above, was that abstention is the validator correctly
doing its job and must never trigger a retry).
**Why this is still safe despite reversing that earlier stance**: the
mechanism that made the earlier stance necessary is unchanged and still
enforced -- every candidate answer, from every provider in the chain, is
checked with the *identical* `validate_claims` logic against the *same*
retrieved evidence before being trusted, and `chat.py` re-validates
whatever the chain returns regardless. Cascading on a vague answer can only
either surface a *better*-grounded answer to the same question from the
same evidence, or exhaust the chain and fall through to the same
abstention a single provider would have produced. It can never let a
*less*-grounded claim through that single-provider validation would have
caught -- the citation-existence check is the gate either way, cascading
just gives more chances to clear it honestly. What would break this
invariant is validating differently inside the cascade than outside it, or
skipping validation under time/cost pressure -- neither is done.
**Why Groq's default model (`openai/gpt-oss-20b`) needed no thinking-budget
workaround unlike Gemini's**: tested live: it's also a "reasoning" model,
but its response separates `reasoning` content from the final `message.content`
and accounts reasoning tokens separately in `usage`, so a generous
`max_tokens` (800) doesn't get silently consumed by hidden reasoning the way
Gemini 3's did before `thinking_budget=0` was added.
**Live-verified with a real, unplanned failure**: mid-session, Gemini's
free-tier daily quota (20 requests) was genuinely exhausted by testing,
producing a real `429 RESOURCE_EXHAUSTED` error. The chain caught it and
Groq answered correctly, grounded, in under 3 seconds -- never reaching the
3.5-minute Ollama step. This is the exact scenario the cascade exists for,
demonstrated by an actual quota limit, not a simulated one.
**Revisit when**: a 4th provider is requested (the list-based design takes
one), or real entailment checking in `claims.py` changes how much cascading
on "vague" answers can actually help (see the superseded entry's revisit
note).

## Scope: core-first, not breadth-first

**Decision**: build chat + RAG + evidence/citations + safety triage +
medication info deeply, with real logic and real tests; other features
(scanner, prescription explainer, doctor finder, multilingual UI, admin)
thinner but functional; defer the full 15-doc set and exhaustive
security/perf/accessibility test suites.
**Why**: the original spec's 43 sections describe a multi-quarter product
build. A single pass that spreads effort evenly across all of it produces
shallow, disconnected pieces everywhere instead of a working, trustworthy
core anywhere -- and the core (grounded answers, no hallucinated citations,
working safety triage) is where the entire product's credibility lives.
**Revisit when**: the core is validated (by the eval suite and manual review)
and there's demand for a specific deferred feature.

## Mock providers by default

**Decision**: `LLMProvider`, `OCRProvider`, `ProviderDirectory`, and
`EmbeddingProvider` are all interfaces with a deterministic mock
implementation as the default, selected via env vars
(`LLM_PROVIDER`/`OCR_PROVIDER`/`MAPS_PROVIDER`). Four real `LLMProvider`
implementations now exist behind the same interface -- `AnthropicProvider`,
`GeminiProvider`, `GroqProvider`, `OllamaProvider` -- all built on shared
prompt-building helpers (`_build_system_prompt`/`_build_user_message` in
`providers/llm.py`) so the citation-marker contract and prompt-injection
framing is identical regardless of which model answers.
**Why**: no API keys were available at build time; building real
architecture behind swappable interfaces means adding a real provider is a
config change later, not a rewrite.
**Update -- no longer purely hypothetical**: real Gemini + Groq credentials
were later provided and are what the live deployment actually runs (see
[DEPLOYMENT.md](DEPLOYMENT.md)) -- this decision's bet paid off exactly as
intended: swapping in real providers took zero code changes. OCR and maps
remain mock-only; no credentials for those have been provided or requested.
**Revisit when**: an OCR provider or a maps/places provider becomes
available (unblocks the Medicine/Prescription/Doctors pages -- see
"Coming Soon gating" below).

## pgvector, not Qdrant

**Decision**: use Postgres + the pgvector extension for the embedding column
instead of a separate vector database.
**Why**: one stateful service to run and back up instead of two, for an
MVP-scale demo corpus (dozens of documents). pgvector's column type is a real
migration path to ANN indexing (`ivfflat`/HNSW) if it's ever needed.
**Revisit when**: corpus size or query volume make Postgres-side vector
search (or the Python-side scoring described below) too slow.

## Retrieval scoring in Python, not in SQL

**Decision**: `hybrid_retrieve` fetches candidate rows by SQL filter, then
computes both the semantic (cosine) and lexical (token overlap) scores in
Python, rather than using pgvector's `<=>` operator or Postgres full-text
`ts_rank`.
**Why**: this makes retrieval logic dialect-independent, so
`tests/test_retrieval.py` runs against SQLite with zero infrastructure. A
`db_types.py` `EmbeddingVector` type decorator uses the real pgvector column
on Postgres and falls back to a plain JSON array on any other dialect, with
no behavioral difference at this scale.
**Revisit when**: corpus size makes brute-force Python scoring measurably
slow; move scoring into SQL/pgvector at that point, not before.

## Hand-rolled i18n, not a framework

**Decision**: `lib/i18n/` is a React context plus three flat JSON dictionaries
(`en`/`hi`/`gu`), not next-intl or a similar library.
**Why**: three static languages and a few dozen UI strings don't justify a
framework's bundle size and configuration surface. Adding a fourth language
is: add a JSON file, add one entry to `SUPPORTED_LANGUAGES`.
**Revisit when**: the string count grows enough to need pluralization rules,
ICU message formatting, or per-language number/date formatting.

## bcrypt directly, not passlib

**Decision**: `security.py` calls the `bcrypt` package's `hashpw`/`checkpw`
directly instead of going through passlib's `CryptContext`.
**Why**: passlib 1.7.4 (its last release, effectively unmaintained) has a
real, reproduced-in-this-repo incompatibility with bcrypt>=4 where its own
internal self-test misfires and raises on ordinary short passwords. bcrypt's
API is two functions; the abstraction layer wasn't earning its keep.
**Revisit when**: never, unless multiple hashing algorithms need to be
supported simultaneously (e.g. migrating away from bcrypt).

## Schema merges

**Decision**: `MedicineAlias` folded into `Medicine.aliases` (a JSON array
column); `ProviderLocation` folded into `Provider` (one row per location,
lat/lng columns directly on the provider).
**Why**: at MVP scale, a medicine has a handful of aliases and a provider
listing is one physical location -- a join table for either buys normalization
that nothing in this codebase needs yet.
**Revisit when**: a provider needs multiple locations under one identity, or
alias metadata (e.g. per-alias region/language) grows beyond a flat string
list.

## Citation markers are a shared wire format, not a prompt-only convention

**Decision**: both the mock and real LLM providers emit
`<sentence>. [[cite:chunk_id]]`, and a single `claims.py` validator enforces
it identically regardless of which provider produced the text.
**Why**: trusting a model (real or mock) to "just cite correctly" is exactly
the kind of prompt-only safety the spec explicitly warns against. Structural
parsing plus dropping anything that doesn't reference an actually-retrieved
chunk id means correctness doesn't depend on provider compliance.
**Revisit when**: never -- this is a hard safety invariant, not a
convenience.

## Local filesystem storage, not S3

**Decision**: `providers/storage.py`'s `FileStorage` interface has one
implementation, `LocalFileStorage`, writing to `STORAGE_DIR` on disk. Every
medicine-scan and prescription upload is persisted this way and recorded as
an `UploadedDocument` row.
**Why**: no object-storage credentials were available at build time, and the
interface boundary is what actually matters for swapping providers later --
adding an S3/GCS implementation later is one new class behind `FileStorage`,
not a change to either upload endpoint.
**Revisit when**: deploying beyond a single instance/disk, or needing signed
URLs for direct client upload.

## Auth: email/password + JWT cookie, no OAuth

**Decision**: registration is email/password, sessions are a JWT in an
httpOnly cookie, with a server-side `auth_sessions` table for revocation.
**Why**: OAuth/social login wasn't requested and adds real complexity
(provider registration, callback handling, account linking) for no stated
requirement.
**Revisit when**: a specific identity provider is requested.

## Coming Soon gating for OCR/Maps-dependent pages

**Decision**: Medicine, Prescription, and Doctors -- the three routes whose
real functionality depends on OCR or a maps/places provider, neither of
which has real credentials -- now render a shared `ComingSoon` component
instead of their previous mock-backed forms. Chat (renamed "MediAssist" in
the nav) is unaffected; it's the one feature with a real, live provider
chain behind it.
**Why**: a mock-backed scanner/upload UI that silently can't do the thing it
visually promises (extract text from a photo, find a real nearby provider)
is worse than being upfront that it's not built yet -- a user who uploads a
prescription photo and gets a canned mock response has been misled, not
helped. The previous mock UI was fine while the whole app was explicitly a
provider-interface demo; it stopped being fine once the app had a real,
live deployment other people would actually visit.
**What was kept, not deleted**: the backend routers, mock providers, and all
existing tests for `/api/medicine`, `/api/prescription`, and `/api/providers`
are untouched -- this is a frontend-only gate. Re-enabling any of the three
is flipping one page back to its previous implementation, not rebuilding a
feature.
**Revisit when**: a real OCR provider or a real maps/places provider gets
credentials -- see the "Mock providers by default" entry above.

## Render (API) + Vercel (web), deployed separately

**Decision**: `services/api` deploys to Render as a Docker web service with
a managed Postgres (`render.yaml` blueprint); `apps/web` deploys to Vercel
with its Root Directory set to `apps/web`. Not one platform for both, and
not a single combined build.
**Why**: Vercel's model (serverless functions, edge-first) fits a Next.js
frontend well but not a stateful FastAPI service with Postgres and
long-running LLM calls; Render's Docker-based web services fit the backend
well but add nothing for a static/SSR Next.js app that Vercel doesn't
already do better. Splitting them is the boring, well-supported path for
each half rather than forcing one host to do both adequately.
**Real gotchas hit getting there, each now fixed and worth recording**:
- **Monorepo Root Directory.** Vercel's GitHub-triggered builds clone the
  whole repo and build from a configurable Root Directory, which defaults
  to the repo root -- wrong for this layout. Manual `vercel --prod` deploys
  run from inside `apps/web` happened to work anyway (the CLI uploads only
  the cwd), which masked the misconfiguration until GitHub-triggered
  auto-deploy hit it with a real "Couldn't find any `pages` or `app`
  directory" build failure. Fixed by setting Root Directory to `apps/web`
  in Project Settings -- there's no `vercel.json` key or CLI command for
  this, it's dashboard/API-only.
- **Hosted Postgres URL scheme.** Render (like most managed Postgres hosts)
  hands out a plain `postgresql://` connection string, which SQLAlchemy
  resolves to the psycopg2 dialect -- not installed here, only psycopg
  (v3) is. Fixed by normalizing the scheme to `postgresql+psycopg://` in
  `app/db.py`, applied to both the app's engine and Alembic's `env.py`
  (which read `database_url` directly, bypassing the app's normalization
  until it got its own call to the same helper).
- **A pip conflict a clean install always would have caught.** `httpx` and
  `pydantic` were pinned to versions older than what `google-genai` (added
  later) actually requires. The local `.venv` never caught this because
  packages were added incrementally over many sessions rather than
  resolved from a clean slate -- Render's clean Docker build did. Fixed by
  dropping the unnecessary `httpx` pin (never imported directly here, only
  by SDKs) and widening `pydantic` to the range `google-genai` needs.
- **No Ollama in production.** The fourth provider needs a persistent
  GPU/CPU box, not a serverless/PaaS host; the deployed cascade is
  Gemini -> Groq, one link shorter than local dev, validated identically.
- **Seed/ingest as a resilient boot step, not a manual one.** Both scripts
  are idempotent (existence/content-hash checked), so they run on every
  container boot rather than requiring a one-time manual Shell command
  that's easy to forget or, on some hosts, hard to even find. The
  network-dependent `ingest_real_sources` step is `|| true`'d so a
  transient fetch failure there can never block the API itself from
  starting -- worst case that boot adds no new content, and the next
  successful one does.
**Revisit when**: traffic or cost outgrows either free tier, or a real
Ollama-equivalent hosted-GPU option becomes worth the cost for the fourth
provider.
