from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

SQLALCHEMY_DATABASE_URL = "sqlite:///./watson.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def ensure_runtime_schema():
    """
    Lightweight dev migration for SQLite. SQLAlchemy create_all does not add
    columns to an existing watson.db, so keep additive run audit fields safe.
    """
    if engine.dialect.name != "sqlite":
        return

    run_columns = {
        "execution_mode": "VARCHAR DEFAULT 'local' NOT NULL",
        "gemini_interaction_ids": "JSON",
        "gemini_environment_id": "VARCHAR",
    }
    insight_columns = {
        "source": "VARCHAR DEFAULT 'analysis' NOT NULL",
        "evidence_strength": "FLOAT",
        "citations": "JSON",
        "playbook_id": "VARCHAR",
        "research_job": "VARCHAR",
        "report_id": "VARCHAR",
        "research_job_id": "VARCHAR",
        "origin_insight_id": "VARCHAR",
    }

    with engine.begin() as connection:
        existing_run_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(runs)")).fetchall()
        }
        for column_name, column_type in run_columns.items():
            if column_name not in existing_run_columns:
                connection.execute(
                    text(f"ALTER TABLE runs ADD COLUMN {column_name} {column_type}")
                )

        existing_insight_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(insights)")).fetchall()
        }
        for column_name, column_type in insight_columns.items():
            if column_name not in existing_insight_columns:
                connection.execute(
                    text(f"ALTER TABLE insights ADD COLUMN {column_name} {column_type}")
                )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
