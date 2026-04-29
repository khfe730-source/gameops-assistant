"""MCP server exposing past incident records via FastMCP tools."""

import logging
import sys

from mcp.server.fastmcp import FastMCP

from mock_data.generators.incident_db import records

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("incident-db-server")


@mcp.tool()
def list_recent_incidents(hours: int = 24) -> dict:
    """Return incidents that started within the last N hours."""
    result = records.list_recent(hours)
    logger.info("list_recent_incidents hours=%d -> %d records", hours, len(result))
    return {"incidents": result, "count": len(result)}


@mcp.tool()
def get_incident(incident_id: str) -> dict:
    """Return full detail for a single incident by ID."""
    inc = records.get_by_id(incident_id)
    logger.info("get_incident id=%s -> %s", incident_id, "found" if inc else "not found")
    if inc is None:
        return {"error": f"incident '{incident_id}' not found"}
    return inc


@mcp.tool()
def search_incidents_by_type(incident_type: str) -> dict:
    """Return all past incidents matching the given type.

    Args:
        incident_type: one of ccu_spike | queue_stuck | error_spike | zone_latency
    """
    result = records.search_by_type(incident_type)  # type: ignore[arg-type]
    logger.info("search_incidents_by_type type=%s -> %d records", incident_type, len(result))
    return {"incidents": result, "count": len(result)}


@mcp.tool()
def get_resolution_steps(incident_type: str) -> dict:
    """Return resolution steps and lessons learned from past incidents of the given type.

    Args:
        incident_type: one of ccu_spike | queue_stuck | error_spike | zone_latency
    """
    result = records.get_resolutions(incident_type)  # type: ignore[arg-type]
    logger.info("get_resolution_steps type=%s -> %d entries", incident_type, len(result))
    return {"resolutions": result, "count": len(result)}


if __name__ == "__main__":
    mcp.run()
