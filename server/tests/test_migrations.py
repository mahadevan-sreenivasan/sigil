from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sigil_server.db import run_migrations


@pytest.mark.asyncio
async def test_migrations_create_visitors_and_signal_sets_tables():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        await run_migrations(engine)

        async with engine.connect() as conn:
            tables = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            )
            table_names = [row[0] for row in tables.fetchall()]

        assert "visitors" in table_names
        assert "signal_sets" in table_names
    finally:
        await engine.dispose()
