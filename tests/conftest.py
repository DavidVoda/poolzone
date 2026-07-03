from collections.abc import Iterator

import pytest
from sqlalchemy.orm import Session

from libpoolzone.storage.engine import get_engine, get_session_factory


@pytest.fixture(scope="session")
def engine():
    """Engine bound to the TEST database. Migrations must already be applied."""
    return get_engine(test=True)


@pytest.fixture()
def db_session(engine) -> Iterator[Session]:
    """A session wrapped in a transaction that is rolled back at the end of each test.

    This keeps tests fast (no schema reset) and isolated (no test data leaks
    between tests).
    """
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = get_session_factory(test=True)
    session = SessionLocal(bind=connection, join_transaction_mode="create_savepoint")

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
