from sqlalchemy import create_engine, text
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finance.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {}
engine_kwargs = {"pool_pre_ping": True}

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def run_migrations():
    """Add missing columns to existing tables"""
    with engine.connect() as conn:
        # Add user_id to monthly_plans if not exists
        conn.execute(text("""
            ALTER TABLE monthly_plans 
            ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)
        """))
        # Add user_id to yearly_plans if not exists
        conn.execute(text("""
            ALTER TABLE yearly_plans 
            ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)
        """))
        # Set existing records to user id 1
        conn.execute(text("""
            UPDATE monthly_plans SET user_id = 1 WHERE user_id IS NULL
        """))
        conn.execute(text("""
            UPDATE yearly_plans SET user_id = 1 WHERE user_id IS NULL
        """))
        conn.commit()