"""Tests for mock_data.generators.logs.entries and log_search_server tools."""

from datetime import datetime, timezone

import pytest

from mock_data.generators.logs import entries

_SEED = 42
_NOW = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# generate_logs
# ---------------------------------------------------------------------------

def test_generate_logs_returns_correct_count():
    logs = entries.generate_logs("normal", _SEED, _NOW)
    assert len(logs) == entries._ENTRY_COUNT


def test_generate_logs_has_required_fields():
    logs = entries.generate_logs("normal", _SEED, _NOW)
    for entry in logs:
        for field in ("timestamp", "level", "service", "message", "trace_id"):
            assert field in entry, f"missing field: {field}"


def test_generate_logs_valid_levels():
    logs = entries.generate_logs("normal", _SEED, _NOW)
    valid = {"DEBUG", "INFO", "WARN", "ERROR"}
    for entry in logs:
        assert entry["level"] in valid


def test_generate_logs_sorted_newest_first():
    logs = entries.generate_logs("normal", _SEED, _NOW)
    timestamps = [e["timestamp"] for e in logs]
    assert timestamps == sorted(timestamps, reverse=True)


def test_generate_logs_is_deterministic():
    a = entries.generate_logs("normal", _SEED, _NOW)
    b = entries.generate_logs("normal", _SEED, _NOW)
    assert a == b


def test_generate_logs_different_seeds_differ():
    a = entries.generate_logs("normal", 1, _NOW)
    b = entries.generate_logs("normal", 2, _NOW)
    assert a != b


# ---------------------------------------------------------------------------
# search_logs — keyword filter
# ---------------------------------------------------------------------------

def test_search_logs_empty_filters_returns_entries():
    result = entries.search_logs("normal", _SEED, _NOW)
    assert len(result) > 0


def test_search_logs_keyword_filter():
    result = entries.search_logs("normal", _SEED, _NOW, keyword="login")
    assert all("login" in e["message"].lower() for e in result)


def test_search_logs_keyword_case_insensitive():
    lower = entries.search_logs("normal", _SEED, _NOW, keyword="session")
    upper = entries.search_logs("normal", _SEED, _NOW, keyword="SESSION")
    assert lower == upper


def test_search_logs_keyword_no_match_returns_empty():
    result = entries.search_logs("normal", _SEED, _NOW, keyword="xyzzy_not_exist")
    assert result == []


# ---------------------------------------------------------------------------
# search_logs — service filter
# ---------------------------------------------------------------------------

def test_search_logs_service_filter():
    result = entries.search_logs("normal", _SEED, _NOW, service="auth")
    assert all(e["service"] == "auth" for e in result)
    assert len(result) > 0


def test_search_logs_unknown_service_returns_empty():
    result = entries.search_logs("normal", _SEED, _NOW, service="unknown-svc")
    assert result == []


# ---------------------------------------------------------------------------
# search_logs — level filter
# ---------------------------------------------------------------------------

def test_search_logs_level_filter():
    result = entries.search_logs("normal", _SEED, _NOW, level="INFO")
    assert all(e["level"] == "INFO" for e in result)
    assert len(result) > 0


def test_search_logs_level_error_filter():
    result = entries.search_logs("normal", _SEED, _NOW, level="ERROR")
    assert all(e["level"] == "ERROR" for e in result)


# ---------------------------------------------------------------------------
# search_logs — time window and limit
# ---------------------------------------------------------------------------

def test_search_logs_zero_minutes_returns_empty():
    result = entries.search_logs("normal", _SEED, _NOW, minutes=0)
    assert result == []


def test_search_logs_respects_limit():
    result = entries.search_logs("normal", _SEED, _NOW, minutes=60, limit=5)
    assert len(result) <= 5


def test_search_logs_large_window_returns_all():
    result = entries.search_logs("normal", _SEED, _NOW, minutes=60, limit=entries._ENTRY_COUNT)
    assert len(result) == entries._ENTRY_COUNT


# ---------------------------------------------------------------------------
# get_error_logs
# ---------------------------------------------------------------------------

def test_get_error_logs_all_errors():
    result = entries.get_error_logs("incident_error_spike", _SEED, _NOW, minutes=60)
    assert all(e["level"] == "ERROR" for e in result)
    assert len(result) > 0


def test_get_error_logs_service_filter():
    result = entries.get_error_logs("incident_error_spike", _SEED, _NOW, service="postgres", minutes=60)
    assert all(e["service"] == "postgres" for e in result)
    assert all(e["level"] == "ERROR" for e in result)


def test_get_error_logs_normal_has_fewer_than_incident():
    normal_errors = entries.get_error_logs("normal", _SEED, _NOW, minutes=60)
    incident_errors = entries.get_error_logs("incident_error_spike", _SEED, _NOW, minutes=60)
    assert len(incident_errors) > len(normal_errors)


# ---------------------------------------------------------------------------
# get_log_stats
# ---------------------------------------------------------------------------

def test_get_log_stats_has_required_keys():
    stats = entries.get_log_stats("normal", _SEED, _NOW)
    for key in ("total", "by_level", "by_service", "window_minutes"):
        assert key in stats


def test_get_log_stats_total_matches_by_level_sum():
    stats = entries.get_log_stats("normal", _SEED, _NOW, minutes=60)
    assert stats["total"] == sum(stats["by_level"].values())


def test_get_log_stats_total_matches_by_service_sum():
    stats = entries.get_log_stats("normal", _SEED, _NOW, minutes=60)
    assert stats["total"] == sum(stats["by_service"].values())


def test_get_log_stats_window_minutes_preserved():
    stats = entries.get_log_stats("normal", _SEED, _NOW, minutes=15)
    assert stats["window_minutes"] == 15


def test_get_log_stats_incident_has_more_errors():
    normal_stats = entries.get_log_stats("normal", _SEED, _NOW, minutes=60)
    incident_stats = entries.get_log_stats("incident_error_spike", _SEED, _NOW, minutes=60)
    normal_errors = normal_stats["by_level"].get("ERROR", 0)
    incident_errors = incident_stats["by_level"].get("ERROR", 0)
    assert incident_errors > normal_errors


# ---------------------------------------------------------------------------
# tail_logs
# ---------------------------------------------------------------------------

def test_tail_logs_returns_entries():
    result = entries.tail_logs("normal", _SEED, _NOW)
    assert len(result) > 0


def test_tail_logs_respects_limit():
    result = entries.tail_logs("normal", _SEED, _NOW, limit=5)
    assert len(result) <= 5


def test_tail_logs_service_filter():
    result = entries.tail_logs("normal", _SEED, _NOW, service="redis", limit=50)
    assert all(e["service"] == "redis" for e in result)


def test_tail_logs_are_newest_first():
    result = entries.tail_logs("normal", _SEED, _NOW, limit=50)
    timestamps = [e["timestamp"] for e in result]
    assert timestamps == sorted(timestamps, reverse=True)


# ---------------------------------------------------------------------------
# incident scenario — spot checks
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario", [
    "incident_ccu_spike",
    "incident_queue_stuck",
    "incident_error_spike",
    "incident_zone_latency",
])
def test_incident_scenario_has_warn_or_error(scenario: str):
    logs = entries.generate_logs(scenario, _SEED, _NOW)
    elevated = [e for e in logs if e["level"] in ("WARN", "ERROR")]
    assert len(elevated) > 0


def test_zone_latency_incident_logs_mention_ap_northeast():
    logs = entries.generate_logs("incident_zone_latency", _SEED, _NOW)
    zone_logs = [e for e in logs if "ap-northeast-1" in e["message"]]
    assert len(zone_logs) > 0


def test_queue_stuck_incident_logs_mention_redis():
    logs = entries.generate_logs("incident_queue_stuck", _SEED, _NOW)
    redis_logs = [e for e in logs if e["service"] == "redis"]
    assert len(redis_logs) > 0
