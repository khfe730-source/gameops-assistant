"""MCP server exposing game server metrics via FastMCP tools."""

import logging
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from mock_data.metrics_generator import (
    generate_ccu,
    generate_error_rate,
    generate_latency,
    generate_matchmaking_queue,
)

logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
logger = logging.getLogger(__name__)

_SEED = 42

mcp = FastMCP("metrics-server")


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


@mcp.tool()
def get_ccu() -> dict:
    """Return current concurrent user count."""
    value = generate_ccu(_SEED, _now())
    logger.info("get_ccu -> %d", value)
    return {"ccu": value, "timestamp": _now().isoformat()}


@mcp.tool()
def get_matchmaking_queue() -> dict:
    """Return matchmaking queue depth and average wait time."""
    data = generate_matchmaking_queue(_SEED, _now())
    logger.info("get_matchmaking_queue -> %s", data)
    return {**data, "timestamp": _now().isoformat()}


@mcp.tool()
def get_error_rate() -> dict:
    """Return error rate percentage and total error count over the last minute."""
    data = generate_error_rate(_SEED, _now())
    logger.info("get_error_rate -> %s", data)
    return {**data, "timestamp": _now().isoformat()}


@mcp.tool()
def get_latency() -> dict:
    """Return p50/p95/p99 latency per server zone."""
    data = generate_latency(_SEED, _now())
    logger.info("get_latency -> %s", data)
    return {"zones": data, "timestamp": _now().isoformat()}


if __name__ == "__main__":
    mcp.run()
