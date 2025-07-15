# app/data/db.py

from sqlalchemy import create_engine, Column, Integer, Text, TIMESTAMP
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
from sqlalchemy.sql import func

# Define base and engine
Base = declarative_base()
engine = create_engine(settings.DB_PATH, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Define Comparison table
class Comparison(Base):
    __tablename__ = "comparisons"
    id = Column(Integer, primary_key=True, index=True)
    tibco_response = Column(Text, nullable=False)
    python_response = Column(Text, nullable=False)
    differences = Column(Text, nullable=False)
    metrics = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())  # ← FIXED

    # created_at = Column(TIMESTAMP, server_default="CURRENT_TIMESTAMP")


# Create the table
Base.metadata.create_all(bind=engine)


# DB Handler class
class DBHandler:
    def __init__(self):
        self.db = SessionLocal()

    def insert_comparison(self, tibco: str, python: str, diff: str, metrics: str):
        record = Comparison(
            tibco_response=tibco,
            python_response=python,
            differences=diff,
            metrics=metrics
        )
        self.db.add(record)
        self.db.commit()

    def fetch_all_differences(self, limit: int = 10):
        # return self.db.query(Comparison).order_by(Comparison.created_at.desc()).all()
        return (
            self.db.query(Comparison)
            .order_by(Comparison.created_at.desc())
            .limit(limit)
            .all()
        )

    def __del__(self):
        self.db.close()