import datetime
from sqlalchemy import Column, String, Text, DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./storage/initiatives.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class Initiative(Base):
    __tablename__ = "initiatives"

    id = Column(String, primary_key=True, index=True)          # UUID
    objective_hash = Column(String, index=True, unique=True)   # SHA-256 of normalised objective
    objective = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False)                  # Full CompanyOSResponse JSON
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


def init_db():
    """Create tables and storage directory if not present."""
    os.makedirs("storage", exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
