import pytest

from orchestrator.database import get_session, init_db


@pytest.fixture
def db_session():
    init_db("sqlite:///:memory:")
    session = get_session()
    yield session
    session.close()
