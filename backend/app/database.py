from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
SQLALCHEMY_DATABASE_URL = f"sqlite:///{BASE_DIR / 'recipes.db'}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Columns added after v0.1 — applied non-destructively to existing SQLite DBs via ADD COLUMN.
_RECIPE_COLUMN_DDL = {
    "prep_time_min": "INTEGER",
    "cook_time_min": "INTEGER",
    "servings": "INTEGER",
    "dietary_flags": "TEXT",
    "nutrition": "TEXT",
    "source_url": "TEXT",
    "source_platform": "VARCHAR(40)",
    "source_context_text": "TEXT",
    "thumbnail_url": "TEXT",
}


def ensure_schema() -> None:
    """Create tables, then add any missing recipe columns without dropping existing data."""
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    if "recipes" not in inspector.get_table_names():
        return
    existing = {col["name"] for col in inspector.get_columns("recipes")}
    missing = {name: ddl for name, ddl in _RECIPE_COLUMN_DDL.items() if name not in existing}
    if not missing:
        return
    with engine.begin() as conn:
        for name, ddl in missing.items():
            conn.execute(text(f"ALTER TABLE recipes ADD COLUMN {name} {ddl}"))
