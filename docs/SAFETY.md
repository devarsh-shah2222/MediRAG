# Safety Architecture

MediRAG's product principle: INFORM -> TRIAGE -> NAVIGATE -> PREPARE, never
DIAGNOSE -> PRESCRIBE. Safety is not delegated to a system prompt; it's a
layer that runs *before* retrieval and generation and can short-circuit them
entirely.

## Layers implemented

| Layer | Where | What it does |
|---|---|---|
| 1. Input classification | `safety/classifier.py` | Rule-based (regex/keyword) categorization of every incoming message into `normal`/`urgent`/`emergency`, plus independent policy flags (dosage-change request, pregnancy, children, allergy, drug interaction, diagnosis request, prescription-only request, certainty-seeking). Runs before anything else in `routers/chat.py`. |
| 2. Risk rules | same | Emergency-level categories: severe breathing difficulty, loss of consciousness, severe chest symptoms, severe allergic reaction, uncontrolled bleeding, severe neurological symptoms, severe confusion, self-harm crisis language. |
| 3. Evidence filtering | `rag/retrieval.py` | Evidence-sufficiency threshold; no chunk clearing the bar means no generation, only abstention. |
| 4. LLM answer constraints | `providers/llm.py` | Shared system prompt (all four real providers -- Anthropic, Gemini, Groq, Ollama -- plus the mock, via the same builder) explicitly forbids diagnosis/prescription/dose changes and mandates per-sentence citation. |
| 5. Post-generation claim validation | `rag/claims.py` | Strips any sentence not tied to an actually-retrieved chunk id; abstains outright if most of the answer is unsupported. |
| 6. Emergency response policy | `routers/chat.py`, `safety/emergency.py` | An `emergency`-level message never reaches retrieval/generation. It returns a fixed, short response plus emergency actions and region-configurable contact numbers. |
| 7. Audit logging | `SafetyEvent` table | Every non-`normal` classification is persisted with its category list and a truncated input excerpt. |
| 8. Human escalation / navigation | `safety/emergency.py`, `/doctors` | "Find Nearby Hospital" / "Find a Doctor" actions. There is no live human handoff (chat-to-human) in this build -- see limitations below. |

## Why rules, not a model, for classification

A keyword/regex classifier is auditable (you can read every pattern), zero
added latency, deterministic, and directly testable with input/expected-
category pairs -- `tests/test_safety_classifier.py` has explicit
false-positive regression cases (ordinary questions like "What is paracetamol
used for?" must never trigger urgent/emergency) alongside the true-positive
cases. This is a real ceiling: a determined or unusually-phrased description
of an emergency could miss every pattern. The mitigation path if this proves
insufficient in the eval suite is to add a model-based *second opinion* on
top of this layer, never to replace it -- defense in depth means the
deterministic layer stays even if a probabilistic one is added.

## Emergency response contract

When `classify()` returns `level == "emergency"`:

1. No retrieval, no generation, no evidence is attached.
2. The response is `mode: "emergency_navigation"` with a fixed short intro
   sentence (never a long AI explanation before the actions).
3. Actions are exactly "Call Emergency Service" and "Find Nearby Hospital".
4. Emergency contact numbers come from the `application_settings` table
   (seeded per region: US/GB/IN in `scripts/seed.py`), never hardcoded into
   the response-building code. If a region has no configured contacts, the
   UI shows "not configured for your region yet" rather than guessing a
   number that might be wrong for the user's country.

## High-risk categories and how they're handled

Policy flags (`dosage_change_request`, `pregnancy`, `children`,
`allergy_mentioned`, `drug_interaction`, `diagnosis_request`,
`prescription_only_request`, `certainty_seeking`) are detected independently
of the urgency level and are surfaced to callers (`routers/medicine.py`
returns an explicit "About changing a dose" warning banner when
`dosage_change_request` is flagged -- the backend behavior is unchanged and
tested, though the Medicine page that would render it is currently gated
behind Coming Soon, see [DECISIONS.md](DECISIONS.md)). They do not currently
alter the chat
generation prompt itself beyond what the base system prompt already forbids
-- the answer is still whatever the grounded RAG pipeline produces, softened
by the disclaimer. This is a real gap: a more complete implementation would
route each policy flag to a category-specific response template. Deferred,
tracked here rather than silently absent.

## Known limitations

- No live human/on-call escalation channel.
- Classifier is English-pattern-only; Hindi/Gujarati emergency phrases in the
  user's own words would not be recognized. Currently a non-issue in
  practice -- there's no in-product way to change the request language
  either, since the language selector was removed as unnecessary at this
  stage (see [DECISIONS.md](DECISIONS.md)) and chat requests always send
  `language: "en"` -- but worth revisiting together if language selection
  returns, since fixing one without the other would be misleading.
- Self-harm crisis detection returns the same generic emergency UI as a
  physical emergency; a dedicated crisis-line response (distinct wording,
  distinct resources) is not implemented.
