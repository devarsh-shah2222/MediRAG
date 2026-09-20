from app.db import _normalize_database_url


def test_upgrades_plain_postgresql_scheme_to_psycopg_dialect() -> None:
    assert _normalize_database_url("postgresql://user:pw@host/db") == "postgresql+psycopg://user:pw@host/db"


def test_upgrades_postgres_scheme_to_psycopg_dialect() -> None:
    # Some hosts (e.g. Render, Heroku-style URLs) use the postgres:// alias.
    assert _normalize_database_url("postgres://user:pw@host/db") == "postgresql+psycopg://user:pw@host/db"


def test_leaves_already_dialected_and_sqlite_urls_untouched() -> None:
    assert _normalize_database_url("postgresql+psycopg://user:pw@host/db") == "postgresql+psycopg://user:pw@host/db"
    assert _normalize_database_url("sqlite:///./dev.db") == "sqlite:///./dev.db"
