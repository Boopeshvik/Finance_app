import os
from sqlalchemy import create_engine, text
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

        # ── monthly_plans / yearly_plans user_id ──
        conn.execute(text("""
            ALTER TABLE monthly_plans
            ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)
        """))
        conn.execute(text("""
            ALTER TABLE yearly_plans
            ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)
        """))
        conn.execute(text("""
            UPDATE monthly_plans SET user_id = 1 WHERE user_id IS NULL
        """))
        conn.execute(text("""
            UPDATE yearly_plans SET user_id = 1 WHERE user_id IS NULL
        """))

        # ── investments table new columns ──────────
        conn.execute(text("""
            ALTER TABLE investments
            ADD COLUMN IF NOT EXISTS start_date DATE
        """))
        conn.execute(text("""
            ALTER TABLE investments
            ADD COLUMN IF NOT EXISTS total_invested FLOAT DEFAULT 0
        """))
        conn.execute(text("""
            ALTER TABLE investments
            ADD COLUMN IF NOT EXISTS current_value FLOAT DEFAULT 0
        """))
        conn.execute(text("""
            ALTER TABLE investments
            ADD COLUMN IF NOT EXISTS notes VARCHAR
        """))

        # Set start_date for any existing rows missing it
        conn.execute(text("""
            UPDATE investments
            SET start_date = '2026-01-01'
            WHERE start_date IS NULL
        """))

        # Remove old columns from investments
        for old_col in ['month', 'year', 'amount_invested']:
            try:
                conn.execute(text(f"""
                    ALTER TABLE investments
                    DROP COLUMN IF EXISTS {old_col}
                """))
            except Exception:
                pass

        # ── investment_history table ───────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS investment_history (
                id SERIAL PRIMARY KEY,
                investment_id INTEGER REFERENCES investments(id),
                user_id INTEGER REFERENCES users(id),
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                amount_added FLOAT DEFAULT 0,
                current_value FLOAT NOT NULL,
                note VARCHAR
            )
        """))

        # ── transaction_templates table ────────────
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS transaction_templates (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                name VARCHAR NOT NULL,
                type VARCHAR NOT NULL,
                category VARCHAR NOT NULL,
                amount FLOAT NOT NULL,
                description VARCHAR,
                sort_order INTEGER DEFAULT 0
            )
        """))

        conn.commit()