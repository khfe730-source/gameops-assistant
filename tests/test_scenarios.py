"""Tests for mock_data.scenarios and mock_data.generators.incident."""

import json
from datetime import datetime
from pathlib import Path


from mock_data.scenarios import (
    Scenario,
    get_all_metrics,
    get_ccu,
    get_error_rate,
    get_latency,
    get_matchmaking_queue,
)

SEED = 42
TS = datetime(2026, 4, 29, 21, 0, 0)
FIXTURES_DIR = Path(__file__).parent.parent / "mock_data" / "fixtures"


# ---------------------------------------------------------------------------
# Normal scenario — must match base generators
# ---------------------------------------------------------------------------


class TestNormalScenario:
    def test_ccu_positive(self):
        assert get_ccu(Scenario.NORMAL, SEED, TS) > 0

    def test_queue_shape(self):
        result = get_matchmaking_queue(Scenario.NORMAL, SEED, TS)
        assert "queue_length" in result and "avg_wait_seconds" in result

    def test_error_rate_below_threshold(self):
        rate = get_error_rate(Scenario.NORMAL, SEED, TS)["rate_percent"]
        assert rate < 5.0

    def test_latency_all_zones_present(self):
        zones = get_latency(Scenario.NORMAL, SEED, TS)
        assert {"ap-northeast-1", "ap-northeast-2", "us-west-2"}.issubset(zones)


# ---------------------------------------------------------------------------
# incident_ccu_spike
# ---------------------------------------------------------------------------


class TestIncidentCcuSpike:
    def test_ccu_is_3x_normal(self):
        spike = get_ccu(Scenario.INCIDENT_CCU_SPIKE, SEED, TS)
        normal = get_ccu(Scenario.NORMAL, SEED, TS)
        assert spike == normal * 3

    def test_queue_longer_than_normal(self):
        spike = get_matchmaking_queue(Scenario.INCIDENT_CCU_SPIKE, SEED, TS)
        normal = get_matchmaking_queue(Scenario.NORMAL, SEED, TS)
        assert spike["queue_length"] > normal["queue_length"]

    def test_queue_wait_above_300s(self):
        assert get_matchmaking_queue(Scenario.INCIDENT_CCU_SPIKE, SEED, TS)["avg_wait_seconds"] >= 300.0

    def test_error_rate_elevated(self):
        rate = get_error_rate(Scenario.INCIDENT_CCU_SPIKE, SEED, TS)["rate_percent"]
        assert rate >= 5.0


# ---------------------------------------------------------------------------
# incident_queue_stuck
# ---------------------------------------------------------------------------


class TestIncidentQueueStuck:
    def test_ccu_unchanged(self):
        assert get_ccu(Scenario.INCIDENT_QUEUE_STUCK, SEED, TS) == get_ccu(Scenario.NORMAL, SEED, TS)

    def test_queue_wait_above_900s(self):
        assert get_matchmaking_queue(Scenario.INCIDENT_QUEUE_STUCK, SEED, TS)["avg_wait_seconds"] >= 900.0

    def test_queue_length_larger_than_normal(self):
        stuck = get_matchmaking_queue(Scenario.INCIDENT_QUEUE_STUCK, SEED, TS)
        normal = get_matchmaking_queue(Scenario.NORMAL, SEED, TS)
        assert stuck["queue_length"] > normal["queue_length"]


# ---------------------------------------------------------------------------
# incident_error_spike
# ---------------------------------------------------------------------------


class TestIncidentErrorSpike:
    def test_error_rate_above_15_percent(self):
        rate = get_error_rate(Scenario.INCIDENT_ERROR_SPIKE, SEED, TS)["rate_percent"]
        assert rate >= 15.0

    def test_total_errors_high(self):
        assert get_error_rate(Scenario.INCIDENT_ERROR_SPIKE, SEED, TS)["total_errors"] >= 800

    def test_ccu_unchanged(self):
        assert get_ccu(Scenario.INCIDENT_ERROR_SPIKE, SEED, TS) == get_ccu(Scenario.NORMAL, SEED, TS)


# ---------------------------------------------------------------------------
# incident_zone_latency
# ---------------------------------------------------------------------------


class TestIncidentZoneLatency:
    def test_affected_zone_p50_above_400ms(self):
        zones = get_latency(Scenario.INCIDENT_ZONE_LATENCY, SEED, TS)
        assert zones["ap-northeast-1"]["p50_ms"] >= 400.0

    def test_other_zones_unchanged(self):
        spike_zones = get_latency(Scenario.INCIDENT_ZONE_LATENCY, SEED, TS)
        normal_zones = get_latency(Scenario.NORMAL, SEED, TS)
        for zone in ("ap-northeast-2", "us-west-2"):
            assert spike_zones[zone] == normal_zones[zone]

    def test_percentile_order_preserved(self):
        zones = get_latency(Scenario.INCIDENT_ZONE_LATENCY, SEED, TS)
        z = zones["ap-northeast-1"]
        assert z["p50_ms"] <= z["p95_ms"] <= z["p99_ms"]


# ---------------------------------------------------------------------------
# get_all_metrics
# ---------------------------------------------------------------------------


class TestGetAllMetrics:
    def test_contains_all_keys(self):
        result = get_all_metrics(Scenario.NORMAL, SEED, TS)
        assert {"scenario", "timestamp", "ccu", "matchmaking_queue", "error_rate", "latency"}.issubset(result)

    def test_scenario_field_matches_input(self):
        for scenario in Scenario:
            result = get_all_metrics(scenario, SEED, TS)
            assert result["scenario"] == scenario.value

    def test_deterministic(self):
        a = get_all_metrics(Scenario.NORMAL, SEED, TS)
        b = get_all_metrics(Scenario.NORMAL, SEED, TS)
        assert a == b


# ---------------------------------------------------------------------------
# Fixture files
# ---------------------------------------------------------------------------


class TestFixtures:
    def test_all_fixture_files_exist(self):
        for scenario in Scenario:
            path = FIXTURES_DIR / f"{scenario.value}.json"
            assert path.exists(), f"Missing fixture: {path}"

    def test_fixture_matches_generator(self):
        """Fixture snapshots must match scenario generators at the reference timestamp."""
        for scenario in Scenario:
            path = FIXTURES_DIR / f"{scenario.value}.json"
            with path.open() as f:
                fixture = json.load(f)
            live = get_all_metrics(scenario, SEED, TS)
            assert fixture["ccu"] == live["ccu"], f"{scenario.value}: ccu mismatch"
            assert fixture["error_rate"] == live["error_rate"], f"{scenario.value}: error_rate mismatch"
            assert fixture["matchmaking_queue"] == live["matchmaking_queue"], f"{scenario.value}: queue mismatch"
