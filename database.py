import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite by default. For PostgreSQL or MySQL set DATABASE_URL, for example:
#   postgresql+psycopg2://user:password@localhost/placement
#   mysql+pymysql://user:password@localhost/placement
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./placement.db")
args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
