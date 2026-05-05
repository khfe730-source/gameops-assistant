"""Integration tests: MCP server tool functions → mock_data pipeline."""

import mcp_servers.incident_db_server as incident_db_srv
import mcp_servers.log_search_server as log_srv
import mcp_servers.metrics_server as metrics_srv
from mock_data.scenarios import Scenario

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INCIDENT_TYPES = ["ccu_spike", "queue_stuck", "error_spike", "zone_latency"]


def _set_scenario(monkeypatch, scenario: Scenario) -> None:
    monkeypatch.setattr(metrics_srv, "_SCENARIO", scenario)
    monkeypatch.setattr(log_srv, "_SCENARIO", scenario)


# ---------------------------------------------------------------------------
# TestMetricsMCPServer — response shape + scenario signal
# ---------------------------------------------------------------------------


class TestMetricsMCPServer:
    def test_ccu_metrics_shape(self):
        result = metrics_srv.get_ccu_metrics()
        assert {"ccu", "scenario", "timestamp"}.issubset(result)
        assert isinstance(result["ccu"], int)

    def test_queue_metrics_shape(self):
        result = metrics_srv.get_matchmaking_queue_metrics()
        assert {"queue_length", "avg_wait_seconds", "scenario", "timestamp"}.issubset(result)

    def test_error_rate_metrics_shape(self):
        result = metrics_srv.get_error_rate_metrics()
        assert {"rate_percent", "total_errors", "scenario", "timestamp"}.issubset(result)

    def test_latency_metrics_shape(self):
        result = metrics_srv.get_latency_metrics()
        assert "zones" in result
        assert {"ap-northeast-1", "ap-northeast-2", "us-west-2"}.issubset(result["zones"])

    def test_scenario_field_reflects_patch(self, monkeypatch):
        monkeypatch.setattr(metrics_srv, "_SCENARIO", Scenario.INCIDENT_ERROR_SPIKE)
        assert metrics_srv.get_ccu_metrics()["scenario"] == "incident_error_spike"

    def test_ccu_spike_ccu_elevated(self, monkeypatch):
        normal = metrics_srv.get_ccu_metrics()["ccu"]
        monkeypatch.setattr(metrics_srv, "_SCENARIO", Scenario.INCIDENT_CCU_SPIKE)
        spike = metrics_srv.get_ccu_metrics()["ccu"]
        assert spike > normal

    def test_ccu_spike_queue_wait_above_300s(self, monkeypatch):
        monkeypatch.setattr(metrics_srv, "_SCENARIO", Scenario.INCIDENT_CCU_SPIKE)
        assert metrics_srv.get_matchmaking_queue_metrics()["avg_wait_seconds"] >= 300.0

    def test_queue_stuck_wait_above_900s(self, monkeypatch):
        monkeypatch.setattr(metrics_srv, "_SCENARIO", Scenario.INCIDENT_QUEUE_STUCK)
        assert metrics_srv.get_matchmaking_queue_metrics()["avg_wait_seconds"] >= 900.0

    def test_error_spike_rate_above_15pct(self, monkeypatch):
        monkeypatch.setattr(metrics_srv, "_SCENARIO", Scenario.INCIDENT_ERROR_SPIKE)
        assert metrics_srv.get_error_rate_metrics()["rate_percent"] >= 15.0

    def test_zone_latency_affected_zone_p99_high(self, monkeypatch):
        monkeypatch.setattr(metrics_srv, "_SCENARIO", Scenario.INCIDENT_ZONE_LATENCY)
        zones = metrics_srv.get_latency_metrics()["zones"]
        assert zones["ap-northeast-1"]["p99_ms"] >= 5000.0

    def test_zone_latency_other_zones_normal(self, monkeypatch):
        monkeypatch.setattr(metrics_srv, "_SCENARIO", Scenario.INCIDENT_ZONE_LATENCY)
        zones = metrics_srv.get_latency_metrics()["zones"]
        for zone in ("ap-northeast-2", "us-west-2"):
            assert zones[zone]["p99_ms"] < 500.0

    def test_normal_error_rate_below_5pct(self, monkeypatch):
        monkeypatch.setattr(metrics_srv, "_SCENARIO", Scenario.NORMAL)
        assert metrics_srv.get_error_rate_metrics()["rate_percent"] < 5.0


# ---------------------------------------------------------------------------
# TestIncidentDBMCPServer — CRUD consistency + all types covered
# ---------------------------------------------------------------------------


class TestIncidentDBMCPServer:
    def test_list_recent_incidents_shape(self):
        result = incident_db_srv.list_recent_incidents()
        assert {"incidents", "count"}.issubset(result)
        assert result["count"] == len(result["incidents"])

    def test_list_count_decreases_with_shorter_window(self):
        wide = incident_db_srv.list_recent_incidents(hours=9999)
        narrow = incident_db_srv.list_recent_incidents(hours=1)
        assert wide["count"] >= narrow["count"]

    def test_get_incident_found(self):
        incidents = incident_db_srv.list_recent_incidents(hours=9999)["incidents"]
        first_id = incidents[0]["incident_id"]
        result = incident_db_srv.get_incident(first_id)
        assert result["incident_id"] == first_id
        assert "root_cause" in result

    def test_get_incident_not_found_returns_error(self):
        result = incident_db_srv.get_incident("INC-DOES-NOT-EXIST")
        assert "error" in result

    def test_search_by_type_returns_matching_type(self):
        for inc_type in _INCIDENT_TYPES:
            result = incident_db_srv.search_incidents_by_type(inc_type)
            assert result["count"] > 0
            for inc in result["incidents"]:
                assert inc["type"] == inc_type

    def test_get_resolution_steps_all_types_have_results(self):
        for inc_type in _INCIDENT_TYPES:
            result = incident_db_srv.get_resolution_steps(inc_type)
            assert result["count"] > 0
            assert len(result["resolutions"]) > 0

    def test_resolution_steps_contain_steps_field(self):
        result = incident_db_srv.get_resolution_steps("error_spike")
        for entry in result["resolutions"]:
            assert "resolution_steps" in entry

    def test_search_and_list_ids_are_consistent(self):
        all_ids = {
            inc["incident_id"]
            for inc in incident_db_srv.list_recent_incidents(hours=9999)["incidents"]
        }
        for inc_type in _INCIDENT_TYPES:
            for inc in incident_db_srv.search_incidents_by_type(inc_type)["incidents"]:
                assert inc["incident_id"] in all_ids


# ---------------------------------------------------------------------------
# TestLogSearchMCPServer — response shape + scenario signal
# ---------------------------------------------------------------------------


class TestLogSearchMCPServer:
    def test_error_logs_shape(self, monkeypatch):
        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.NORMAL)
        result = log_srv.get_error_logs()
        assert {"logs", "count", "scenario"}.issubset(result)
        assert result["count"] == len(result["logs"])

    def test_log_stats_shape(self, monkeypatch):
        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.NORMAL)
        result = log_srv.get_log_stats()
        assert {"total", "by_level", "by_service", "window_minutes", "scenario"}.issubset(result)

    def test_normal_scenario_has_no_error_logs(self, monkeypatch):
        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.NORMAL)
        result = log_srv.get_error_logs(minutes=60)
        assert result["count"] == 0

    def test_error_spike_has_error_logs(self, monkeypatch):
        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.INCIDENT_ERROR_SPIKE)
        result = log_srv.get_error_logs(minutes=60, limit=200)
        assert result["count"] > 0

    def test_error_spike_stats_error_count_exceeds_normal(self, monkeypatch):
        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.NORMAL)
        normal_errors = log_srv.get_log_stats(minutes=60)["by_level"].get("ERROR", 0)

        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.INCIDENT_ERROR_SPIKE)
        spike_errors = log_srv.get_log_stats(minutes=60)["by_level"].get("ERROR", 0)

        assert spike_errors > normal_errors

    def test_queue_stuck_logs_contain_matchmaking_errors(self, monkeypatch):
        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.INCIDENT_QUEUE_STUCK)
        result = log_srv.get_error_logs(service="matchmaking", minutes=60, limit=200)
        assert result["count"] > 0

    def test_zone_latency_logs_contain_ap_northeast_1(self, monkeypatch):
        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.INCIDENT_ZONE_LATENCY)
        result = log_srv.search_logs(keyword="ap-northeast-1", minutes=60, limit=200)
        assert result["count"] > 0

    def test_all_error_log_entries_are_error_level(self, monkeypatch):
        monkeypatch.setattr(log_srv, "_SCENARIO", Scenario.INCIDENT_ERROR_SPIKE)
        result = log_srv.get_error_logs(minutes=60, limit=200)
        for entry in result["logs"]:
            assert entry["level"] == "ERROR"


# ---------------------------------------------------------------------------
# TestCrossServerConsistency — same scenario tells same story across servers
# ---------------------------------------------------------------------------


class TestCrossServerConsistency:
    def test_error_spike_metrics_and_logs_both_signal_error(self, monkeypatch):
        _set_scenario(monkeypatch, Scenario.INCIDENT_ERROR_SPIKE)
        error_rate = metrics_srv.get_error_rate_metrics()["rate_percent"]
        error_log_count = log_srv.get_error_logs(minutes=60, limit=200)["count"]
        assert error_rate >= 15.0
        assert error_log_count > 0

    def test_queue_stuck_metrics_and_logs_both_signal_queue(self, monkeypatch):
        _set_scenario(monkeypatch, Scenario.INCIDENT_QUEUE_STUCK)
        queue_wait = metrics_srv.get_matchmaking_queue_metrics()["avg_wait_seconds"]
        mm_errors = log_srv.get_error_logs(service="matchmaking", minutes=60, limit=200)["count"]
        assert queue_wait >= 900.0
        assert mm_errors > 0

    def test_zone_latency_metrics_and_logs_both_signal_zone(self, monkeypatch):
        _set_scenario(monkeypatch, Scenario.INCIDENT_ZONE_LATENCY)
        p99 = metrics_srv.get_latency_metrics()["zones"]["ap-northeast-1"]["p99_ms"]
        zone_logs = log_srv.search_logs(keyword="ap-northeast-1", minutes=60, limit=200)["count"]
        assert p99 >= 5000.0
        assert zone_logs > 0

    def test_normal_scenario_no_anomalies_in_either_server(self, monkeypatch):
        _set_scenario(monkeypatch, Scenario.NORMAL)
        error_rate = metrics_srv.get_error_rate_metrics()["rate_percent"]
        queue_wait = metrics_srv.get_matchmaking_queue_metrics()["avg_wait_seconds"]
        error_logs = log_srv.get_error_logs(minutes=60, limit=200)["count"]
        assert error_rate < 5.0
        assert queue_wait < 300.0
        assert error_logs == 0
