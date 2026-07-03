from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from libpoolzone.settings import Settings


@lru_cache(maxsize=2)
def get_engine(*, test: bool = False) -> Engine:
    settings = Settings()
    url = settings.database_url_test if test else settings.database_url
    return create_engine(url, pool_pre_ping=True, future=True)


def get_session_factory(*, test: bool = False) -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(test=test), expire_on_commit=False)


@contextmanager
def session_scope(*, test: bool = False):
    """Provide a transactional scope: commit on success, rollback on error."""
    Session = get_session_factory(test=test)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
