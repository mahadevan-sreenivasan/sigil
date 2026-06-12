from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"


def make_async_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(make_async_url(database_url))


def _adapt_for_sqlite(sql: str) -> str:
    """Adapt PostgreSQL DDL to SQLite-compatible DDL for testing."""
    sql = sql.replace("TIMESTAMPTZ", "TEXT")
    sql = sql.replace("BIGSERIAL", "INTEGER")
    sql = sql.replace("JSONB", "TEXT")
    sql = re.sub(r"DEFAULT\s+NOW\(\)", "DEFAULT (datetime('now'))", sql, flags=re.IGNORECASE)
    return sql


async def run_migrations(engine: AsyncEngine) -> None:
    is_sqlite = str(engine.url).startswith("sqlite")

    async with engine.begin() as conn:
        for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            sql = migration_file.read_text()
            if is_sqlite:
                sql = _adapt_for_sqlite(sql)
            for statement in sql.split(";"):
                statement = statement.strip()
                if statement:
                    await conn.execute(text(statement))
