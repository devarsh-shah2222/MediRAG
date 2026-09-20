from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.providers.directory import ProviderSearchParams, get_provider_directory
from app.schemas import ProviderResponse

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderResponse])
def list_providers(
    city: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    specialty: str | None = None,
    provider_type: str | None = None,
    max_distance_km: float | None = None,
    emergency_only: bool = False,
    db: Session = Depends(get_db),
) -> list[ProviderResponse]:
    directory = get_provider_directory(db)
    results = directory.search(
        ProviderSearchParams(
            city=city,
            lat=lat,
            lng=lng,
            specialty=specialty,
            provider_type=provider_type,
            max_distance_km=max_distance_km,
            emergency_only=emergency_only,
        )
    )
    return [ProviderResponse(**r.__dict__) for r in results]


@router.get("/{provider_id}", response_model=ProviderResponse)
def get_provider(provider_id: str, db: Session = Depends(get_db)) -> ProviderResponse:
    directory = get_provider_directory(db)
    result = directory.get(provider_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found.")
    return ProviderResponse(**result.__dict__)
