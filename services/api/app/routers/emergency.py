from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.safety.emergency import get_emergency_contacts

router = APIRouter(prefix="/api/emergency-information", tags=["emergency"])


@router.get("")
def emergency_information(region: str | None = None, db: Session = Depends(get_db)) -> dict:
    resolved_region = region or get_settings().default_region
    return {"region": resolved_region, "contacts": get_emergency_contacts(db, resolved_region)}
