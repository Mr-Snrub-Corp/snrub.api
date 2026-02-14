from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    echo=True,  # Set to False in production
)


# Create all tables
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


# Session dependency
def get_session():
    with Session(engine) as session:
        yield session
