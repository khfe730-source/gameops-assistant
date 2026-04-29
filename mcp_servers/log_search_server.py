"""MCP server exposing game server log search, mocking Loki/Elasticsearch."""

import logging
import os
import sys
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from mock_data.scenarios import Scenario
from mock_data.generators.logs import entries

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

_SEED = 42
_SCENARIO = Scenario(os.environ.get("LOG_SCENARIO", Scenario.NORMAL.value))

mcp = FastMCP("log-search-server")


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


@mcp.tool()
def search_logs(
    keyword: str = "",
    service: str = "",
    level: str = "",
    minutes: int = 30,
    limit: int = 50,
) -> dict:
    """Search logs by keyword, service, and level over the last N minutes.

    Args:
        keyword: case-insensitive substring match on message (empty = all)
        service: filter by service name — auth|matchmaking|game-session|api-gateway|user-service|postgres|redis|game-server (empty = all)
        level: filter by log level — DEBUG|INFO|WARN|ERROR (empty = all)
        minutes: time window in minutes (default 30)
        limit: max entries to return (default 50)
    """
    result = entries.search_logs(_SCENARIO.value, _SEED, _now(), keyword, service, level, minutes, limit)
    logger.info(
        "search_logs keyword=%r service=%r level=%r minutes=%d -> %d entries",
        keyword, service, level, minutes, len(result),
    )
    return {"logs": result, "count": len(result), "scenario": _SCENARIO.value}


@mcp.tool()
def get_error_logs(
    service: str = "",
    minutes: int = 30,
    limit: int = 50,
) -> dict:
    """Return ERROR-level logs within the last N minutes, optionally filtered by service.

    Args:
        service: filter by service name (empty = all services)
        minutes: time window in minutes (default 30)
        limit: max entries to return (default 50)
    """
    result = entries.get_error_logs(_SCENARIO.value, _SEED, _now(), service, minutes, limit)
    logger.info("get_error_logs service=%r minutes=%d -> %d entries", service, minutes, len(result))
    return {"logs": result, "count": len(result), "scenario": _SCENARIO.value}


@mcp.tool()
def get_log_stats(minutes: int = 30) -> dict:
    """Return log count statistics by level and by service over the last N minutes.

    Args:
        minutes: time window in minutes (default 30)
    """
    result = entries.get_log_stats(_SCENARIO.value, _SEED, _now(), minutes)
    logger.info("get_log_stats minutes=%d -> total=%d", minutes, result["total"])
    return {**result, "scenario": _SCENARIO.value}


@mcp.tool()
def tail_logs(
    service: str = "",
    limit: int = 20,
) -> dict:
    """Return the most recent log entries, optionally filtered by service.

    Args:
        service: filter by service name (empty = all services)
        limit: max entries to return (default 20)
    """
    result = entries.tail_logs(_SCENARIO.value, _SEED, _now(), service, limit)
    logger.info("tail_logs service=%r limit=%d -> %d entries", service, limit, len(result))
    return {"logs": result, "count": len(result), "scenario": _SCENARIO.value}


if __name__ == "__main__":
    mcp.run()
