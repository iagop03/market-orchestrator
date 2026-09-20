from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from orchestrator.state_machine import Base

_engine = None
_SessionFactory: sessionmaker | None = None


def init_db(database_url: str) -> None:
    global _engine, _SessionFactory
    _engine = create_engine(database_url, future=True)
    Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine, future=True)


def get_session() -> Session:
    if _SessionFactory is None:
        raise RuntimeError("init_db() must be called before get_session()")
    return _SessionFactory()
