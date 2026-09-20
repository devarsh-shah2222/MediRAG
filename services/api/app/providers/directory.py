import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import Provider


@dataclass
class ProviderSearchParams:
    city: str | None = None
    lat: float | None = None
    lng: float | None = None
    specialty: str | None = None
    provider_type: str | None = None
    max_distance_km: float | None = None
    emergency_only: bool = False


@dataclass
class ProviderResult:
    id: str
    name: str
    provider_type: str
    specialty: str | None
    address: str
    city: str
    phone: str | None
    website: str | None
    opening_hours: dict | None
    distance_km: float | None
    accepts_emergency: bool
    is_demo: bool


class ProviderDirectory(ABC):
    @abstractmethod
    def search(self, params: ProviderSearchParams) -> list[ProviderResult]: ...

    @abstractmethod
    def get(self, provider_id: str) -> ProviderResult | None: ...


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _to_result(p: Provider, distance_km: float | None) -> ProviderResult:
    return ProviderResult(
        id=p.id,
        name=p.name,
        provider_type=p.provider_type,
        specialty=p.specialty,
        address=p.address,
        city=p.city,
        phone=p.phone,
        website=p.website,
        opening_hours=p.opening_hours,
        distance_km=distance_km,
        accepts_emergency=p.accepts_emergency,
        is_demo=p.is_demo,
    )


class MockProviderDirectory(ProviderDirectory):
    """Serves the seeded demo Provider dataset (clearly labeled DEMO).

    ponytail: the user asked to mock every external provider for the first
    build, so this queries our own seed data instead of a real Places/Maps
    API. Never fabricates a provider that isn't in the dataset. Upgrade
    trigger: set MAPS_PROVIDER to a real implementation of this interface
    (e.g. Google Places) once a maps API key is available.
    """

    def __init__(self, db: Session):
        self._db = db

    def search(self, params: ProviderSearchParams) -> list[ProviderResult]:
        query = self._db.query(Provider)
        if params.provider_type:
            query = query.filter(Provider.provider_type == params.provider_type)
        if params.specialty:
            query = query.filter(Provider.specialty.ilike(f"%{params.specialty}%"))
        if params.emergency_only:
            query = query.filter(Provider.accepts_emergency.is_(True))
        if params.city and not (params.lat and params.lng):
            query = query.filter(Provider.city.ilike(f"%{params.city}%"))

        providers = query.all()
        results: list[ProviderResult] = []
        for p in providers:
            distance_km = None
            if params.lat is not None and params.lng is not None:
                distance_km = round(_haversine_km(params.lat, params.lng, p.lat, p.lng), 1)
                if params.max_distance_km is not None and distance_km > params.max_distance_km:
                    continue
            results.append(_to_result(p, distance_km))

        results.sort(key=lambda r: (r.distance_km is None, r.distance_km or 0))
        return results

    def get(self, provider_id: str) -> ProviderResult | None:
        p = self._db.query(Provider).filter(Provider.id == provider_id).first()
        return _to_result(p, None) if p else None


def get_provider_directory(db: Session) -> ProviderDirectory:
    return MockProviderDirectory(db)
