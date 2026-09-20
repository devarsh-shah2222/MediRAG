# RAG Architecture

## Pipeline

```
ingestion (txt/md/html/pdf) -> heading-aware chunking -> embedding
  -> hybrid retrieval (semantic + lexical, source-authority boost)
  -> evidence sufficiency check -> generation with inline citation markers
  -> claim validation against retrieved set -> structured response
```

Implementation: `services/api/app/rag/{chunking,ingest,retrieval,claims}.py`.

## Real reference content (`scripts/ingest_real_sources.py`)

The corpus is real content fetched live at ingestion time, not fabricated or
hand-authored, and not scraped from an arbitrary site:

- **openFDA Drug Label API** (`api.fda.gov`) for seven medications (three
  originally, plus metformin/amlodipine/azithromycin/cetirizine added for
  India-relevant coverage -- see below) -- real FDA structured product
  labeling. Public domain U.S. government work.
- **MedlinePlus** (`wsearch.nlm.nih.gov`) for the four health topics -- real
  NIH/National Library of Medicine consumer health summaries. Public domain
  U.S. government work.

**India-specific coverage**: no equivalent structured, publicly-callable API
exists for India (researched CDSCO, India's National Health Portal, and
data.gov.in -- see [DECISIONS.md](DECISIONS.md) for what was actually found).
So "Indian medicines data" here means two things layered on the same real
openFDA content, not a third source: (1) four more medicines that are among
the most commonly prescribed in India, and (2) verified-real Indian brand
names (Crocin, Dolo, Calpol, Brufen, Novamox, Glycomet, Amlong, Amlopres,
Azithral, Alerid -- checked via web search, not asserted from memory)
canonicalized to their generic name at the tokenizer level
(`providers/stopwords.py`'s `_SYNONYM_CANONICAL`), so a query using the brand
name retrieves the real generic-name label content, plus a `synonym_note` on
each medication document naming its Indian brand(s) as citable evidence.

Both are chosen specifically because they're free to reuse with attribution
(no scraping-terms-of-service concern) and because they're structured enough
to parse reliably (JSON for FDA, a documented XML web service for
MedlinePlus) rather than screen-scraping arbitrary HTML.

**Deliberately excluded**: `dosage_and_administration` and any sentence
matching a dosing-frequency pattern ("every 8 hours", "twice daily", etc.),
wherever it appears in the label -- caught live when a dosing-frequency
sentence leaked in through an unrelated field
(`information_for_patients`) and was stripped by `_strip_dosing_sentences`.
MediRAG never repeats a specific dose or frequency, even as quoted,
correctly-cited evidence (see `SAFETY.md`).

**Known content-quality caveats of automated real-source ingestion** (not
present in the demo content it replaced, which was hand-authored to read
cleanly): real FDA labels vary in format between OTC "Drug Facts" labels and
prescription SPL labels, so field selection differs per label
(`_select_sections`) to avoid duplicating the same warning sentence twice
under one heading; some labels include boilerplate noise at the tail of a
field (manufacturer/trademark text) that isn't filtered; MedlinePlus's search
API returns a concise summary, not the full article, so some topics (e.g.
seasonal allergies) have less retrievable content than others. None of this
is a correctness or safety problem -- it's real government text, verbatim
and cited -- just occasionally rougher prose than hand-written demo copy.

## Ingestion (`ingest.py`)

Supports markdown, plain text, HTML (BeautifulSoup, scripts/styles stripped),
and PDF (pypdf, per-page text extraction). Each document is hashed
(`content_hash`); re-ingesting identical content is a no-op, and changed
content bumps `content_version` and re-chunks. Every chunk carries its parent
document's source, title, type, language, jurisdiction, and publication date
through to citation time.

## Chunking (`chunking.py`)

Splits on markdown headings first, so a "Warnings" section is never merged
with "Uses". A section that's still too long (>900 chars) is split further on
sentence boundaries, with the heading text prefixed onto each piece so a
chunk read in isolation still carries its context. Plain text without
headings falls back to paragraph-based splitting.

## Embedding (`providers/embeddings.py`)

`MockEmbeddingProvider` is a deterministic hashing bag-of-words vector (384
dims, pure stdlib + numpy): each token hashes to an index with a
sign-determined by another hash byte, summed and L2-normalized. No model
download, no API key, fully reproducible. **Known limitation**: it only
tokenizes ASCII word characters, so a query typed entirely in Devanagari
(Hindi/Gujarati) script produces zero tokens and will not semantically match
anything -- see `README.md`'s known limitations and the `multilingual-01` eval
case. A real embedding provider (Voyage/OpenAI/Cohere) drops in behind the
same `EmbeddingProvider` interface.

## Tokenization (`providers/stopwords.py`)

A single shared `tokenize`/`tokenize_counts` pair is used by both the mock
embedding and the lexical scorer, so a word is never treated as two different
tokens depending on which one looks at it. Three things happen to every
piece of text: lowercasing and splitting on non-alphanumerics, dropping a
~60-word English stopword list plus a handful of corpus-specific filler words
("commonly", "documented", "condition", "approach(es)") that showed up as
generic across nearly every document, and light plural normalization
("allergies" -> "allergy", "symptoms" -> "symptom") via a five-line suffix
rule -- not a real stemmer.

## Hybrid retrieval (`retrieval.py`)

Score = `0.65 * semantic_cosine + 0.35 * lexical_overlap`, plus a +0.05 boost
for sources typed `government`/`who`/`regulatory`. Both scoring components
run in Python over rows fetched by SQL (filtered by `medical_topic`/`language`
when provided), rather than via Postgres `ts_rank` + pgvector's `<=>`
operator -- this keeps the scoring logic dialect-independent and unit
testable without a running Postgres (see `db_types.py`'s SQLite fallback).
Fine at demo-corpus scale; the upgrade path if a real corpus needs ANN
indexing is documented inline.

Both the embedding and the lexical scorer weight a term by **how often it
appears**, not just whether it appears (log-scaled: `1 + log(tf)`, so a
single mention keeps exactly the credit it always had, and repeated
mentions count for more, uncapped). Without this, a real FDA pain-reliever
label mentioning "the common cold" once, in a list of reasons to take it,
scored identically to the MedlinePlus article that's actually about the
common cold and says so repeatedly -- a real query returned drug labels
instead of the actual reference document until this was fixed
(`tests/test_retrieval.py::test_repeated_topic_word_outranks_incidental_single_mention`).

Lexical overlap is weighted by inverse document frequency computed fresh
over the current candidate set (`_compute_idf`): a word appearing in nearly
every candidate document is nearly worthless as a signal, while a word
appearing in only one or two is a strong one even if it's the *only* word
the query and the source share. A **single** overlapping word is trusted
only if it's genuinely rare -- its IDF must be at least `0.65x` the maximum
achievable IDF for the current candidate set (a *relative*, not absolute,
cutoff: an absolute number tuned against the real ~7-document corpus made
even a maximally-rare word fail in a 3-document test fixture, where IDF
values are inherently smaller). Two or more distinct overlapping words are
trusted regardless of rarity.

This combination of guardrails was reached the hard way, each one fixing a
real failure the previous one caused or missed:

1. No lexical guardrail at all: a nonsense query sharing only the incidental
   word "condition" cleared the evidence bar.
2. "Require 2+ overlapping words": fixed (1), but then "What is hypertension
   and how is it managed?" abstained, because "hypertension" (the *only*
   overlapping word -- the source never says "managed") got the same
   blanket rejection as a truly generic single word.
3. IDF-weighted overlap, no minimum: fixed (2), but a real query about a
   nonexistent condition matched on the word "treatment" alone -- appearing
   in over half the real corpus, not rare, but repeated twice in one chunk,
   and the term-frequency boost let that repetition alone clear the bar.
4. Relative rare-word gate on single-word matches (this version): fixes (3)
   without reintroducing (2).

All four states are pinned down as regression tests in
`tests/test_retrieval.py` and as eval cases in `evals/dataset.jsonl`
(`abstain-01`/`02`, `basic-02`, `basic-03`).

Top 5 results are kept; anything scoring below `SUFFICIENCY_THRESHOLD = 0.28`
is dropped. If nothing clears the bar, retrieval returns empty and the chat
layer abstains rather than generating from nothing. Both this threshold and
`RARE_WORD_RELATIVE_THRESHOLD` were tuned empirically against the eval suite
and a broader manual query set, not picked a priori -- there's no principled
way to derive them analytically from a hash-based mock embedding, only to
check them against real cases and adjust.

## Generation and citation (`providers/llm.py`, `rag/claims.py`)

`MockLLMProvider` (extractive: pulls 1-2 sentences per top chunk),
`AnthropicProvider` (real Claude call), `GeminiProvider` (real Gemini call via
the `google-genai` SDK), `GroqProvider` (real call to Groq's hosted-inference
API via the `groq` SDK), and `OllamaProvider` (real local-model call via the
`ollama` SDK, no API key or internet access needed at inference time -- just
a running Ollama install with a model already pulled) all emit the same wire
format, since the four real providers share the same system-prompt/
evidence-block builders (system-prompted to treat evidence as untrusted data
and to cite every sentence): `<sentence>. [[cite:chunk_id]]`. `claims.py` is
the single enforcement point for all of them -- a locally-run model is not
exempt from citing real evidence just because it's offline.

When `LLM_PROVIDER=gemini`, these aren't independent alternatives but an
ordered chain (`CascadingLLMProvider`: Gemini -> Groq -> Ollama), escalating
on either an exception or a validated-vague answer -- see DECISIONS.md for
why escalating on "vague" is safe here specifically (every candidate is
checked by the same validator below against the same evidence before being
trusted).

- Parses `<sentence>[[cite:ID]]` units with a regex that ties each marker to
  its *immediately preceding* sentence (an earlier version split sentences
  first and looked for markers inside each piece, which let a marker drift
  onto the *next* sentence when multiple cited sentences were concatenated --
  caught by `tests/test_claims.py`).
- A sentence whose marker doesn't reference an actually-retrieved chunk id is
  dropped as unsupported.
- If more than half of the answer's sentences end up unsupported (or none are
  supported at all), the whole response abstains rather than showing a
  partially-hallucinated answer.

This is why prompt injection embedded in a retrieved document is inert by
construction (see `tests/test_chat_api.py::test_retrieved_document_with_injected_instructions_is_treated_as_data`):
the mock provider only ever emits cited excerpts of the retrieved text, and
the Anthropic system prompt explicitly tells the model the evidence block is
data, not instructions, on top of that.

**Known limitation, found live, not yet fixed**: `claims.py` verifies that a
cited chunk id was actually in the retrieved set -- it does NOT verify that
the cited chunk's content actually supports the specific sentence attached
to it. Testing `llama3.2:3b` as a fallback candidate surfaced a real case:
it answered a question about amoxicillin's uses with fabricated content
("treats sexually transmitted infections such as chlamydia and gonorrhea" --
not in any retrieved evidence) and cited a real, retrieved chunk id that
happened to exist, but whose actual content was an unrelated brand-name
note. A *real* citation pointing at the *wrong* text currently passes
validation the same as a correct one. In this instance the answer was still
abstained, but only by the accident of that response also using the wrong
marker syntax (`[chunk_id: X]` instead of `[[cite:X]]`) -- had the syntax
been right, the fabricated claim would have shipped with a technically-valid
citation. This is why `llama3.1:8b` was chosen over `llama3.2:3b` for the
Ollama fallback role (see DECISIONS.md) rather than patching around it, and
it's the concrete argument for a real fix: entailment checking between a
cited chunk's text and the sentence citing it (embedding similarity, or a
second small model call), not just id-existence checking. Not built here --
flagged as the highest-value next hardening step for the claim validator.

## What's NOT implemented

- Reranking model (cross-encoder or similar) -- the authority/freshness boost
  is the only re-scoring beyond the base hybrid score.
- Real embeddings / non-Latin-script semantic search.
- Table-preserving chunking (tables in source PDFs are flattened to text by
  pypdf's extraction, not specially preserved).
- Citation *entailment* checking (see the known limitation above) -- only
  citation *existence* is currently verified.
