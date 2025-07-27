# app/data/db.py
from sqlalchemy import create_engine, Column, Integer, Text, TIMESTAMP, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import text, func
from app.config import settings
from typing import Optional, List, Type
import logging
import json  # Added import


logger = logging.getLogger(__name__)

Base = declarative_base()
engine = create_engine(settings.DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Comparison(Base):
    __tablename__ = "comparisons"
    id = Column(Integer, primary_key=True, index=True)
    tibco_response = Column(Text, nullable=False)
    python_response = Column(Text, nullable=False)
    differences = Column(Text, nullable=False)
    metrics = Column(Text, nullable=False)
    content_type1 = Column(Text, nullable=True)
    content_type2 = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


def check_and_update_schema():
    # No changes to this function
    try:
        inspector = inspect(engine)
        if not inspector.has_table('comparisons'):
            Base.metadata.create_all(bind=engine)
            logger.info("Created new comparisons table")
            return
        columns = inspector.get_columns('comparisons')
        existing_columns = {col['name'] for col in columns}
        needed_columns = {'content_type1', 'content_type2'}
        missing_columns = needed_columns - existing_columns
        if missing_columns:
            with engine.begin() as conn:
                for column in missing_columns:
                    stmt = text(f"ALTER TABLE comparisons ADD COLUMN {column} TEXT")
                    conn.execute(stmt)
            logger.info(f"Added missing columns: {missing_columns}")
    except Exception as e:
        logger.error(f"Failed to update database schema: {str(e)}")
        raise


def initialize_database():
    # No changes to this function
    try:
        check_and_update_schema()
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialization complete")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise RuntimeError(f"Database initialization failed: {str(e)}")


initialize_database()


# dependency to get a DB session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# The DBHandler class is replaced by standalone functions that accept a db session.
#
# OLD CODE:
# class DBHandler:
#     def __init__(self):
#         self.db = SessionLocal()
#
#     def insert_comparison(self, tibco: str, python: str, diff: str, metrics: dict,
#                           content_type1: str = None, content_type2: str = None):
#         try:
#             metrics_str = metrics if isinstance(metrics, str) else json.dumps(metrics)
#             record = Comparison(
#                 tibco_response=tibco,
#                 python_response=python,
#                 differences=diff,
#                 metrics=metrics_str,
#                 content_type1=content_type1,
#                 content_type2=content_type2
#             )
#             self.db.add(record)
#             self.db.commit()
#             self.db.refresh(record)
#             return record
#         except Exception as e:
#             self.db.rollback()
#             logger.error(f"Failed to insert comparison: {str(e)}")
#             raise
#
#     def fetch_all_differences(self, limit: int = 10) -> list[Type[Comparison]] | None:
#         try:
#             return (
#                 self.db.query(Comparison)
#                 .order_by(Comparison.created_at.desc())
#                 .limit(limit)
#                 .all()
#             )
#         except Exception as e:
#             logger.error(f"Database query failed: {str(e)}")
#             return None
#         finally:
#             self.close()
#
#     def fetch_latest_comparison(self) -> Optional[Comparison]:
#         try:
#             return (
#                 self.db.query(Comparison)
#                 .order_by(Comparison.created_at.desc())
#                 .first()
#             )
#         except Exception as e:
#             logger.error(f"Failed to fetch latest comparison: {str(e)}")
#             return None
#         finally:
#             self.close()
#
#     def close(self):
#         self.db.close()
#
#     def __del__(self):
#         self.close()

# NEW CODE: Standalone functions
def insert_comparison(db: Session, tibco: str, python: str, diff: str, metrics: str,
                      content_type1: str = None, content_type2: str = None):
    try:
        # metrics are already passed as a JSON string
        record = Comparison(
            tibco_response=tibco,
            python_response=python,
            differences=diff,
            metrics=metrics,
            content_type1=content_type1,
            content_type2=content_type2
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to insert comparison: {str(e)}")
        raise


def fetch_all_differences(db: Session, limit: int = 10) -> list[Type[Comparison]] | None:
    try:
        return (
            db.query(Comparison)
            .order_by(Comparison.created_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        logger.error(f"Database query failed: {str(e)}")
        return None


def fetch_latest_comparison(db: Session) -> Optional[Comparison]:
    try:
        return (
            db.query(Comparison)
            .order_by(Comparison.created_at.desc())
            .first()
        )
    except Exception as e:
        logger.error(f"Failed to fetch latest comparison: {str(e)}")
        return None
