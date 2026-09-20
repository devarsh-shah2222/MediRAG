"""Replaces the demo reference library with real content fetched live from
two authoritative, public-domain U.S. government sources:

- openFDA Drug Label API (api.fda.gov) -- FDA structured product labeling,
  for the seven medications.
- MedlinePlus (medlineplus.gov / wsearch.nlm.nih.gov) -- National Library of
  Medicine consumer health topic summaries, for the four health topics.

Both are real HTTP calls made at run time (not fabricated, not scraped from
an arbitrary site) and both are public domain U.S. government works, so
reuse with attribution is not a licensing concern. Every ingested document
keeps its real source URL.

No equivalent structured, publicly-callable API exists for India: CDSCO
(India's drug regulator) publishes only static approved-drug-name lists, no
label content via API; India's National Health Portal is a web portal, not
an API. Rather than scrape a commercial pharmacy site and present it as
authoritative (explicitly against this project's own sourcing policy -- see
SAFETY.md/README.md), India-relevant coverage here means: (a) four more
medicines heavily prescribed in India (metformin, amlodipine, azithromycin,
cetirizine) via the same real openFDA pipeline -- the pharmacology is the
same regardless of country even though the label itself is FDA-sourced --
and (b) verified-real Indian brand names as query synonyms (see
`synonym_note` below and `providers/stopwords.py`'s `_SYNONYM_CANONICAL`),
so "Crocin" or "Glycomet" retrieves the right generic-name content.

ponytail: two sources, hand-picked per topic, fetched with the stdlib's
urllib rather than adding an HTTP client dependency (httpx is already a
dev/test-only dependency, not a runtime one). Upgrade trigger: needing more
sources or more topics than fit comfortably in one small script -> promote
to a proper admin-driven ingestion workflow via the existing
POST /api/rag/ingest endpoint instead of a one-off script.

Usage: python -m scripts.ingest_real_sources
"""
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from app.db import Base, SessionLocal, engine
from app.models import RAGSource
from app.providers.embeddings import get_embedding_provider
from app.rag.ingest import ingest_document

FDA_SOURCE_NAME = "U.S. FDA (openFDA Drug Label API)"
MEDLINEPLUS_SOURCE_NAME = "MedlinePlus (U.S. National Library of Medicine)"
DEMO_SOURCE_NAME = "MediRAG Demo Reference Library"

MEDICATIONS = [
    {
        "generic_name": "acetaminophen", "route": "ORAL", "title": "Paracetamol (Acetaminophen)",
        "medical_topic": "paracetamol",
        # FDA labels only ever say "acetaminophen" (the US name) -- never
        # "paracetamol" -- so a user asking about "paracetamol" (the name
        # used almost everywhere outside the US) would get zero token
        # overlap with the real label text and abstain. This is a factual
        # naming note, not a medical claim, so it needs no citation.
        "synonym_note": (
            "Acetaminophen is also commonly called paracetamol in many countries outside the United "
            "States, including India, where it is sold under brand names such as Crocin, Dolo, and Calpol."
        ),
    },
    {
        "generic_name": "ibuprofen", "route": "ORAL", "title": "Ibuprofen", "medical_topic": "ibuprofen",
        "synonym_note": "Ibuprofen is sold in India under brand names such as Brufen.",
    },
    {
        "generic_name": "amoxicillin", "route": "ORAL", "title": "Amoxicillin", "medical_topic": "amoxicillin",
        "synonym_note": "Amoxicillin is sold in India under brand names such as Novamox.",
    },
    {
        "generic_name": "metformin", "route": "ORAL", "title": "Metformin", "medical_topic": "metformin",
        "synonym_note": "Metformin is sold in India under brand names such as Glycomet.",
    },
    {
        "generic_name": "amlodipine", "route": "ORAL", "title": "Amlodipine", "medical_topic": "amlodipine",
        "synonym_note": "Amlodipine is sold in India under brand names such as Amlong and Amlopres.",
    },
    {
        "generic_name": "azithromycin", "route": "ORAL", "title": "Azithromycin", "medical_topic": "azithromycin",
        "synonym_note": "Azithromycin is sold in India under brand names such as Azithral.",
    },
    {
        "generic_name": "cetirizine", "route": "ORAL", "title": "Cetirizine", "medical_topic": "cetirizine",
        "synonym_note": "Cetirizine is sold in India under brand names such as Alerid.",
    },
]

HEALTH_TOPICS = [
    {"term": "common cold", "title": "Common Cold", "medical_topic": "common_cold"},
    {"term": "high blood pressure", "title": "Hypertension (High Blood Pressure)", "medical_topic": "hypertension"},
    {"term": "seasonal allergies", "title": "Seasonal Allergies (Allergic Rhinitis)", "medical_topic": "seasonal_allergies"},
    {"term": "type 2 diabetes", "title": "Type 2 Diabetes", "medical_topic": "type_2_diabetes"},
]

# Dosage fields are deliberately never used -- MediRAG never recommends or
# repeats a specific dose (see SAFETY.md); "how_supplied" is excluded too
# since for Rx labels it's just NDC package codes, not useful storage info.
#
# Strips two kinds of label boilerplate before it becomes chunk text:
# OTC Drug Facts panels repeat their own section name as the first word
# ("Uses temporarily relieves..."), and Rx SPL labels prefix a numbered,
# all-caps section header ("6 ADVERSE REACTIONS The following...").
_LEADING_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)*\s+")
_LEADING_CAPS_RE = re.compile(r"^(?:[A-Z][A-Z/\-]*\s+)+")
_LEADING_OTC_LABEL_RE = re.compile(
    r"^(Uses?|Warnings?|Purpose|Directions|Other information|"
    r"Active ingredient(?:s)?(?: \(in each [^)]*\))?|Do not use|"
    r"Ask a doctor(?: or pharmacist)?|Stop use|When using this product)\s*[:.]?\s*",
    re.IGNORECASE,
)
_HIGHLIGHT_SPAN_RE = re.compile(r"</?span[^>]*>")


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
# Dosage fields (dosage_and_administration) are already excluded, but a
# specific dosing frequency can still leak in through a field that's mostly
# about something else -- caught live: information_for_patients (mapped to
# "Precautions") included "amoxicillin tablets may be taken every 8 hours or
# every 12 hours, depending on the dose prescribed" inside an otherwise
# unrelated paragraph about counseling patients. MediRAG never repeats a
# specific dose or frequency (see SAFETY.md), so any sentence matching this
# pattern is dropped wherever it appears, not just from the obvious field.
_DOSING_SENTENCE_RE = re.compile(
    r"\bevery \d+ (?:to \d+ )?hours?\b|\b\d+ times? (?:a|per) day\b|"
    r"\bonce (?:daily|a day)\b|\btwice (?:daily|a day)\b|\b\d+ times daily\b|"
    r"\bdepending on the dose\b",
    re.IGNORECASE,
)


def _strip_dosing_sentences(text: str) -> str:
    sentences = _SENTENCE_SPLIT_RE.split(text)
    kept = [s for s in sentences if not _DOSING_SENTENCE_RE.search(s)]
    return " ".join(kept)


def _clean_label_text(text: str) -> str:
    text = _LEADING_NUMBER_RE.sub("", text)
    text = _LEADING_CAPS_RE.sub("", text)
    text = _LEADING_OTC_LABEL_RE.sub("", text)
    text = _strip_dosing_sentences(text)
    return text.strip()


def fetch_fda_label(generic_name: str, route: str | None) -> dict | None:
    query = f'openfda.generic_name.exact:"{generic_name.upper()}"'
    if route:
        query += f"+AND+openfda.route:{route}"
    # openFDA's query DSL uses a literal "+" as its AND operator, so the
    # search value can't go through urlencode() (which would escape it to
    # %2B and change its meaning) -- quote() with "+" in the safe set instead.
    url = f"https://api.fda.gov/drug/label.json?search={urllib.parse.quote(query, safe='+:\"')}&limit=1"
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.load(resp)
    results = data.get("results") or []
    return results[0] if results else None


def _select_sections(label: dict) -> dict[str, str]:
    """Chooses which label fields become which heading, favoring the least
    redundant combination. An OTC "Drug Facts" label's `warnings` field
    already contains its do-not-use/stop-use/ask-a-doctor sub-clauses as one
    flowing paragraph -- also including those fields individually produced
    the same sentence two or three times under the same heading (caught by
    inspecting real ingested output, not a hypothetical). Rx SPL labels
    don't have a combined `warnings` field at all, so they fall through to
    their own (non-overlapping) fields.
    """
    sections: dict[str, list[str]] = {}

    def add(heading: str, field: str) -> None:
        values = label.get(field)
        if not values:
            return
        text = _clean_label_text(" ".join(values))
        if text:
            sections.setdefault(heading, []).append(text)

    add("Active Ingredient", "active_ingredient")
    add("Active Ingredient", "description")
    add("Medicine Class", "purpose")
    add("Uses", "indications_and_usage")
    add("Common Side Effects", "adverse_reactions")
    add("Interactions", "drug_interactions")
    add("Storage", "storage_and_handling")

    # boxed_warning is FDA's most serious warning callout ("black box") --
    # always included, never redundant with the other warning fields below.
    add("Warnings", "boxed_warning")

    if label.get("warnings"):
        add("Warnings", "warnings")
    else:
        add("Warnings", "contraindications")
        add("Warnings", "warnings_and_cautions")
        add("Warnings", "do_not_use")
        add("Warnings", "stop_use")

    add("Precautions", "when_using")
    add("Precautions", "ask_doctor")
    add("Precautions", "ask_doctor_or_pharmacist")
    add("Precautions", "information_for_patients")

    return {heading: " ".join(paragraphs) for heading, paragraphs in sections.items()}


def build_medication_markdown(title: str, label: dict, synonym_note: str | None = None) -> str:
    lines = [f"# {title}", ""]
    if synonym_note:
        lines.append(synonym_note)
        lines.append("")
    for heading, text in _select_sections(label).items():
        lines.append(f"## {heading}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)


def fetch_medlineplus_topic(term: str) -> dict | None:
    url = "https://wsearch.nlm.nih.gov/ws/query?" + urllib.parse.urlencode(
        {"db": "healthTopics", "term": term, "retmax": 1}
    )
    with urllib.request.urlopen(url, timeout=15) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes)
    document = root.find(".//document")
    if document is None:
        return None
    doc_url = document.attrib.get("url")
    summary = next(
        (c.text for c in document.findall("content") if c.attrib.get("name") == "FullSummary" and c.text),
        None,
    )
    if not summary:
        return None
    return {"summary": _HIGHLIGHT_SPAN_RE.sub("", summary), "url": doc_url}


def seed_real_sources() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    embedding_provider = get_embedding_provider()

    try:
        demo_source = db.query(RAGSource).filter(RAGSource.name == DEMO_SOURCE_NAME).first()
        if demo_source:
            db.delete(demo_source)
            db.commit()
            print(f"Removed '{DEMO_SOURCE_NAME}' and its documents.")

        fda_source = db.query(RAGSource).filter(RAGSource.name == FDA_SOURCE_NAME).first()
        if not fda_source:
            fda_source = RAGSource(
                name=FDA_SOURCE_NAME,
                source_type="regulatory",
                jurisdiction="US",
                url="https://open.fda.gov/apis/drug/label/",
                authority_notes=(
                    "U.S. Food and Drug Administration structured product labeling, via the public "
                    "openFDA API. Public domain U.S. government work."
                ),
                update_policy="re-ingested on demand via scripts/ingest_real_sources.py",
            )
            db.add(fda_source)
            db.flush()

        medlineplus_source = db.query(RAGSource).filter(RAGSource.name == MEDLINEPLUS_SOURCE_NAME).first()
        if not medlineplus_source:
            medlineplus_source = RAGSource(
                name=MEDLINEPLUS_SOURCE_NAME,
                source_type="government",
                jurisdiction="US",
                url="https://medlineplus.gov/",
                authority_notes=(
                    "U.S. National Library of Medicine (NIH) consumer health information. "
                    "Public domain U.S. government work."
                ),
                update_policy="re-ingested on demand via scripts/ingest_real_sources.py",
            )
            db.add(medlineplus_source)
            db.flush()

        for med in MEDICATIONS:
            label = fetch_fda_label(med["generic_name"], med.get("route"))
            if not label:
                print(f"WARNING: no openFDA label found for {med['generic_name']}, skipping.")
                continue
            markdown = build_medication_markdown(med["title"], label, med.get("synonym_note"))
            spl_id = label.get("id")
            source_url = f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={spl_id}" if spl_id else None
            result = ingest_document(
                db=db, embedding_provider=embedding_provider, source=fda_source,
                title=med["title"], raw_bytes=markdown.encode("utf-8"), doc_type="markdown",
                medical_topic=med["medical_topic"], jurisdiction="US", url=source_url, is_demo=False,
            )
            print(f"Ingested '{med['title']}' from openFDA: {result.chunk_count} chunks")

        for topic in HEALTH_TOPICS:
            data = fetch_medlineplus_topic(topic["term"])
            if not data:
                print(f"WARNING: no MedlinePlus topic found for '{topic['term']}', skipping.")
                continue
            result = ingest_document(
                db=db, embedding_provider=embedding_provider, source=medlineplus_source,
                title=topic["title"], raw_bytes=data["summary"].encode("utf-8"), doc_type="html",
                medical_topic=topic["medical_topic"], jurisdiction="US", url=data["url"], is_demo=False,
            )
            print(f"Ingested '{topic['title']}' from MedlinePlus: {result.chunk_count} chunks")

        db.commit()
        print("Real source ingestion complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_real_sources()
