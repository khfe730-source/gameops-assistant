"""MCP server exposing game server metrics via FastMCP tools."""

import logging
import os
from datetime import datetime

from mcp.server.fastmcp import FastMCP

from mock_data.scenarios import Scenario, get_ccu, get_error_rate, get_latency, get_matchmaking_queue

logging.basicConfig(level=logging.INFO, stream=__import__("sys").stderr)
logger = logging.getLogger(__name__)

_SEED = 42
_SCENARIO = Scenario(os.environ.get("METRICS_SCENARIO", Scenario.NORMAL.value))

mcp = FastMCP("metrics-server")


def _now() -> datetime:
    """Return current UTC datetime."""
    return datetime.utcnow()


@mcp.tool()
def get_ccu_metrics() -> dict:
    """Return current concurrent user count."""
    value = get_ccu(_SCENARIO, _SEED, _now())
    logger.info("get_ccu [%s] -> %d", _SCENARIO.value, value)
    return {"ccu": value, "scenario": _SCENARIO.value, "timestamp": _now().isoformat()}


@mcp.tool()
def get_matchmaking_queue_metrics() -> dict:
    """Return matchmaking queue depth and average wait time."""
    data = get_matchmaking_queue(_SCENARIO, _SEED, _now())
    logger.info("get_matchmaking_queue [%s] -> %s", _SCENARIO.value, data)
    return {**data, "scenario": _SCENARIO.value, "timestamp": _now().isoformat()}


@mcp.tool()
def get_error_rate_metrics() -> dict:
    """Return error rate percentage and total error count over the last minute."""
    data = get_error_rate(_SCENARIO, _SEED, _now())
    logger.info("get_error_rate [%s] -> %s", _SCENARIO.value, data)
    return {**data, "scenario": _SCENARIO.value, "timestamp": _now().isoformat()}


@mcp.tool()
def get_latency_metrics() -> dict:
    """Return p50/p95/p99 latency per server zone."""
    data = get_latency(_SCENARIO, _SEED, _now())
    logger.info("get_latency [%s] -> %s", _SCENARIO.value, data)
    return {"zones": data, "scenario": _SCENARIO.value, "timestamp": _now().isoformat()}


if __name__ == "__main__":
    mcp.run()
