from sqlmodel import create_engine, text

from app.core.config import settings


def test_can_connect_to_database() -> None:
    engine = create_engine(settings.DATABASE_URL, echo=False)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
