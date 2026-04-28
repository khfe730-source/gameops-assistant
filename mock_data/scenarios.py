"""Scenario-based metrics facade mapping scenario names to generator functions."""

from datetime import datetime
from enum import Enum

from mock_data.generators.metrics import incident as metrics_incident, normal as metrics_normal


class Scenario(str, Enum):
    NORMAL = "normal"
    INCIDENT_CCU_SPIKE = "incident_ccu_spike"
    INCIDENT_QUEUE_STUCK = "incident_queue_stuck"
    INCIDENT_ERROR_SPIKE = "incident_error_spike"
    INCIDENT_ZONE_LATENCY = "incident_zone_latency"


def get_ccu(scenario: Scenario, seed: int, ts: datetime) -> int:
    """Return CCU for the given scenario."""
    match scenario:
        case Scenario.INCIDENT_CCU_SPIKE:
            return metrics_incident.ccu_spike(seed, ts)
        case _:
            return metrics_normal.generate_ccu(seed, ts)


def get_matchmaking_queue(scenario: Scenario, seed: int, ts: datetime) -> dict:
    """Return matchmaking queue metrics for the given scenario."""
    match scenario:
        case Scenario.INCIDENT_CCU_SPIKE:
            return metrics_incident.queue_overloaded(seed, ts)
        case Scenario.INCIDENT_QUEUE_STUCK:
            return metrics_incident.queue_stuck(seed, ts)
        case _:
            return metrics_normal.generate_matchmaking_queue(seed, ts)


def get_error_rate(scenario: Scenario, seed: int, ts: datetime) -> dict:
    """Return error rate metrics for the given scenario."""
    match scenario:
        case Scenario.INCIDENT_ERROR_SPIKE:
            return metrics_incident.error_spike(seed, ts)
        case Scenario.INCIDENT_CCU_SPIKE:
            return metrics_incident.error_elevated(seed, ts)
        case _:
            return metrics_normal.generate_error_rate(seed, ts)


def get_latency(scenario: Scenario, seed: int, ts: datetime) -> dict:
    """Return latency metrics per zone for the given scenario."""
    match scenario:
        case Scenario.INCIDENT_ZONE_LATENCY:
            return metrics_incident.zone_latency_spike(seed, ts)
        case _:
            return metrics_normal.generate_latency(seed, ts)


def get_all_metrics(scenario: Scenario, seed: int, ts: datetime) -> dict:
    """Return a full metrics snapshot for the given scenario."""
    return {
        "scenario": scenario.value,
        "timestamp": ts.isoformat(),
        "ccu": get_ccu(scenario, seed, ts),
        "matchmaking_queue": get_matchmaking_queue(scenario, seed, ts),
        "error_rate": get_error_rate(scenario, seed, ts),
        "latency": get_latency(scenario, seed, ts),
    }
