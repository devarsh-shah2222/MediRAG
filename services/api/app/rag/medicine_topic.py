from sqlalchemy.orm import Session

from app.models import Medicine


def find_medicine_topic(db: Session, query: str) -> str | None:
    """Matches a free-text query against known medicine names/aliases
    (including verified Indian brand names -- see DECISIONS.md) to scope
    retrieval to that medicine's own document, rather than searching the
    whole corpus. Shared by /api/medicine/analyze and /api/chat: a chat
    question naming a specific medicine deserves the same scoped retrieval
    the dedicated medicine page gets, not a global search where that
    medicine's chunks compete against everything else in the corpus.
    """
    lowered = query.lower()
    for medicine in db.query(Medicine).all():
        names = [medicine.name.lower(), *[a.lower() for a in (medicine.aliases or [])]]
        if medicine.generic_name:
            names.append(medicine.generic_name.lower())
        if any(name in lowered for name in names):
            return medicine.medical_topic
    return None
