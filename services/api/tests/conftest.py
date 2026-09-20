import os
import tempfile

import pytest

# Must happen before any `app.*` module import, since app.db builds the engine
# at import time from these settings. Tests run against a throwaway SQLite
# file (not Postgres/pgvector) via the EmbeddingVector dialect fallback --
# see app/db_types.py.
_tmp_fd, _tmp_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_path}"
os.environ["AUTH_SECRET"] = "test-secret"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["OCR_PROVIDER"] = "mock"

from app import models  # noqa: E402,F401 -- registers all tables on Base.metadata
from app.db import Base, SessionLocal, engine  # noqa: E402

Base.metadata.create_all(bind=engine)


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _clean_db():
    yield
    session = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()
