"""Seeds infrastructure data: known-medicine aliases (for medicine-name
matching), demo providers, and default emergency contacts. Safe to re-run.

RAG reference content is NOT seeded here -- see scripts/ingest_real_sources.py,
which fetches real content from openFDA and MedlinePlus. Run this script
first (it creates the tables and the Medicine/Provider/ApplicationSetting
rows other endpoints depend on), then that one.

Usage: python -m scripts.seed
"""
import json
from pathlib import Path

from app.db import Base, SessionLocal, engine
from app.models import ApplicationSetting, Medicine, Provider

SEED_DATA_DIR = Path(__file__).resolve().parent.parent / "seed_data"

# Aliases include verified-real Indian brand names (see DECISIONS.md) so
# /api/medicine/analyze matches them to the right ingested generic-name
# content, the same mechanism as the international brand names.
KNOWN_MEDICINES = [
    {"name": "Paracetamol", "generic_name": "Acetaminophen", "aliases": ["acetaminophen", "tylenol", "crocin", "dolo", "calpol"], "medical_topic": "paracetamol"},
    {"name": "Ibuprofen", "generic_name": "Ibuprofen", "aliases": ["advil", "motrin", "brufen"], "medical_topic": "ibuprofen"},
    {"name": "Amoxicillin", "generic_name": "Amoxicillin", "aliases": ["amoxil", "novamox"], "medical_topic": "amoxicillin"},
    {"name": "Metformin", "generic_name": "Metformin", "aliases": ["glucophage", "glycomet"], "medical_topic": "metformin"},
    {"name": "Amlodipine", "generic_name": "Amlodipine", "aliases": ["norvasc", "amlong", "amlopres"], "medical_topic": "amlodipine"},
    {"name": "Azithromycin", "generic_name": "Azithromycin", "aliases": ["zithromax", "azithral"], "medical_topic": "azithromycin"},
    {"name": "Cetirizine", "generic_name": "Cetirizine", "aliases": ["zyrtec", "alerid"], "medical_topic": "cetirizine"},
]

EMERGENCY_CONTACTS = {
    "US": {"emergency_number": "911", "poison_control": "1-800-222-1222", "note": "United States"},
    "GB": {"emergency_number": "999", "poison_control": None, "note": "United Kingdom"},
    "IN": {"emergency_number": "112", "poison_control": None, "note": "India (unified emergency number)"},
}


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        for med in KNOWN_MEDICINES:
            existing = db.query(Medicine).filter(Medicine.name == med["name"]).first()
            if not existing:
                db.add(Medicine(**med))

        providers_path = SEED_DATA_DIR / "demo_providers.json"
        providers = json.loads(providers_path.read_text())
        existing_count = db.query(Provider).count()
        if existing_count == 0:
            for p in providers:
                db.add(Provider(is_demo=True, **p))
            print(f"Seeded {len(providers)} demo providers.")
        else:
            print(f"Skipped provider seeding, {existing_count} already present.")

        for region, contacts in EMERGENCY_CONTACTS.items():
            key = f"emergency_contacts.{region}"
            setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == key).first()
            if setting:
                setting.value = contacts
            else:
                db.add(ApplicationSetting(key=key, value=contacts, description=f"Emergency contacts for {region}"))

        db.commit()
        print("Seed complete. Run `python -m scripts.ingest_real_sources` next for RAG reference content.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
