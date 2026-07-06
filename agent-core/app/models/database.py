from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

DATABASE_URL = f"mysql+pymysql://{settings.mysql_username}:{settings.mysql_password}@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_db}?charset=utf8mb4"

engine = None
SessionLocal = None
Base = declarative_base()


def get_db():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized")
    return SessionLocal()


def init_db():
    global engine, SessionLocal
    engine = create_engine(DATABASE_URL, echo=False, future=True, pool_size=10, max_overflow=20)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    print("[Database] MySQL connection successful")
