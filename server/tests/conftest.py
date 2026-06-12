from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from sigil_server.db import run_migrations


@pytest.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    await run_migrations(e)
    yield e
    await e.dispose()


@pytest.fixture
async def client(engine):
    from sigil_server.main import create_app

    app = create_app(engine=engine)
    app.state.engine = engine
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
