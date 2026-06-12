from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def prune_expired_data(engine: AsyncEngine, retention_days: int = 180) -> dict[str, int]:
    """Delete signal sets and geolocation history older than *retention_days*,
    then remove orphaned visitors (no signal sets AND no account bindings).

    Returns counts of deleted rows per table.
    """
    is_sqlite = str(engine.url).startswith("sqlite")
    if is_sqlite:
        cutoff_expr = f"datetime('now', '-{retention_days} days')"
    else:
        cutoff_expr = f"NOW() - INTERVAL '{retention_days} days'"

    async with engine.begin() as conn:
        sig_result = await conn.execute(
            text(f"DELETE FROM signal_sets WHERE captured_at < {cutoff_expr}")
        )
        signal_sets_removed = sig_result.rowcount

        geo_result = await conn.execute(
            text(f"DELETE FROM geolocation_history WHERE captured_at < {cutoff_expr}")
        )
        geolocations_removed = geo_result.rowcount

        orphan_result = await conn.execute(
            text(
                "DELETE FROM visitors WHERE visitor_id NOT IN "
                "(SELECT DISTINCT visitor_id FROM signal_sets) "
                "AND visitor_id NOT IN "
                "(SELECT DISTINCT visitor_id FROM account_bindings)"
            )
        )
        visitors_removed = orphan_result.rowcount

    logger.info(
        "Retention pruning complete: signal_sets=%d, geolocations=%d, visitors=%d",
        signal_sets_removed, geolocations_removed, visitors_removed,
    )

    return {
        "signal_sets": signal_sets_removed,
        "geolocations": geolocations_removed,
        "visitors": visitors_removed,
    }
