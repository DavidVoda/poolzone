import os

from libpoolzone.settings import Settings


def test_settings_reads_database_url_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@host:5432/db")
    monkeypatch.setenv("DATABASE_URL_TEST", "postgresql+psycopg://u:p@host:5432/db_test")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://u:p@host:5432/db"
    assert settings.database_url_test == "postgresql+psycopg://u:p@host:5432/db_test"


def test_settings_database_url_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL_TEST", raising=False)

    # Silence .env file discovery for this test
    monkeypatch.setattr(os, "environ", {})

    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
