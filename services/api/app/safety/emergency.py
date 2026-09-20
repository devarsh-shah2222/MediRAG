from sqlalchemy.orm import Session

from app.models import ApplicationSetting

DEFAULT_CONTACTS = {
    "emergency_number": None,
    "poison_control": None,
    "note": "Emergency contact numbers are not configured for your region yet. Please use your local emergency number.",
}


def get_emergency_contacts(db: Session, region: str) -> dict:
    """Emergency numbers are configurable per region via ApplicationSetting
    (seeded data), never hardcoded into the safety/response logic itself."""
    setting = db.query(ApplicationSetting).filter(ApplicationSetting.key == f"emergency_contacts.{region}").first()
    if setting:
        return setting.value
    return DEFAULT_CONTACTS


def build_emergency_actions(region: str) -> list[dict]:
    return [
        {"id": "call_emergency", "label": "Call Emergency Service", "type": "emergency_call"},
        {"id": "find_hospital", "label": "Find Nearby Hospital", "type": "navigate", "target": "/doctors?type=hospital&emergency=true"},
    ]


def build_urgent_actions() -> list[dict]:
    return [
        {"id": "find_doctor", "label": "Find a Doctor Nearby", "type": "navigate", "target": "/doctors"},
        {"id": "prepare_visit", "label": "Prepare Questions for My Visit", "type": "suggested_prompt"},
    ]
