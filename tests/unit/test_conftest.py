from sqlalchemy import text


def test_db_session_fixture_works(db_session):
    result = db_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_two_tests_are_isolated(db_session):
    # If isolation is broken, a leftover from another test would appear.
    # Just assert we can write + read in the same session without conflict.
    db_session.execute(text("CREATE TEMP TABLE t (n int)"))
    db_session.execute(text("INSERT INTO t VALUES (1)"))
    assert db_session.execute(text("SELECT count(*) FROM t")).scalar() == 1
