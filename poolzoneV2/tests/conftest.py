import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.settings import DATABASE_URL

# Tests run against a dedicated DB so the dev DB (with real bootstrap data) is
# never read or written by the suite. Override with TEST_DATABASE_URL if needed.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", DATABASE_URL.rsplit("/", 1)[0] + "/poolzone_test"
)


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DATABASE_URL, future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    """Each test runs in a transaction that is rolled back afterwards."""
    connection = engine.connect()
    trans = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()
