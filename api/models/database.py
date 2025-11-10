from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()
engine = None
SessionLocal = None

def init_database(
    db_user: str,
    db_pass: str,
    db_host: str,
    db_port: int,
    db_name: str,
):
    """
    Initializes the database connection and enables pgvector extension.
    """
    global engine, SessionLocal
    sqlalchemy_database_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(sqlalchemy_database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Enable pgvector extension
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector extension enabled")
    except Exception as e:
        logger.warning(f"Could not enable pgvector extension: {e}")

    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """
    Returns a new database session.
    """
    if not SessionLocal:
        raise Exception("Database has not been initialized. Please call init_database() first.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
