from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from chessmirror.config import get_settings


def make_session_factory() -> sessionmaker:
    """Connect to Postgres and return a factory that opens database sessions."""
    engine = create_engine(
        get_settings().database_url
    )  # the connection pool to Postgres
    return sessionmaker(engine)
