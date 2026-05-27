from sqlalchemy import text

from libpoolzone.storage.engine import get_engine, session_scope


def test_get_engine_returns_a_working_engine(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test"
    )
    monkeypatch.setenv(
        "DATABASE_URL_TEST", "postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test"
    )

    engine = get_engine(test=True)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_session_scope_commits_on_success(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test"
    )
    monkeypatch.setenv(
        "DATABASE_URL_TEST", "postgresql+psycopg://poolzone:poolzone@localhost:5432/poolzone_test"
    )

    with session_scope(test=True) as session:
        result = session.execute(text("SELECT 42"))
        assert result.scalar() == 42
