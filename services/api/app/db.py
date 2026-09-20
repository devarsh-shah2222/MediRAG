from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()


def _normalize_database_url(url: str) -> str:
    # Hosted Postgres providers (Render, Railway, Neon, Supabase, ...) hand out
    # a plain postgresql:// URL, which SQLAlchemy resolves to the psycopg2
    # dialect -- but only psycopg (v3) is installed here. Upgrade the scheme
    # so the same DATABASE_URL works whether it came from a provider or from
    # a hand-written local .env that already specifies +psycopg.
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


engine = create_engine(_normalize_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
