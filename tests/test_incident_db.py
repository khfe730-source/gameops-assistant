"""Tests for mock_data.generators.incident_db.records and incident_db_server tools."""

import pytest

from mock_data.generators.incident_db import records


# ---------------------------------------------------------------------------
# records.list_recent
# ---------------------------------------------------------------------------

def test_list_recent_returns_list():
    result = records.list_recent(hours=24)
    assert isinstance(result, list)


def test_list_recent_large_window_returns_all():
    # 87600 hours = 10 years — should capture every fixture record
    result = records.list_recent(hours=87600)
    assert len(result) == len(records._RECORDS)


def test_list_recent_zero_hours_returns_empty():
    result = records.list_recent(hours=0)
    assert result == []


def test_list_recent_sorted_newest_first():
    result = records.list_recent(hours=87600)
    started_ats = [r["started_at"] for r in result]
    assert started_ats == sorted(started_ats, reverse=True)


# ---------------------------------------------------------------------------
# records.get_by_id
# ---------------------------------------------------------------------------

def test_get_by_id_known():
    inc = records.get_by_id("INC-2026-001")
    assert inc is not None
    assert inc["incident_id"] == "INC-2026-001"
    assert inc["type"] == "ccu_spike"


def test_get_by_id_unknown_returns_none():
    assert records.get_by_id("INC-9999-999") is None


def test_get_by_id_has_required_fields():
    inc = records.get_by_id("INC-2026-001")
    for field in ("incident_id", "type", "severity", "title",
                  "started_at", "resolved_at", "duration_minutes",
                  "affected_components", "summary", "root_cause",
                  "resolution_steps", "lessons_learned"):
        assert field in inc


# ---------------------------------------------------------------------------
# records.search_by_type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("incident_type", ["ccu_spike", "queue_stuck", "error_spike", "zone_latency"])
def test_search_by_type_returns_correct_type(incident_type: str):
    result = records.search_by_type(incident_type)  # type: ignore[arg-type]
    assert len(result) >= 1
    assert all(r["type"] == incident_type for r in result)


def test_search_by_type_sorted_newest_first():
    result = records.search_by_type("ccu_spike")
    started_ats = [r["started_at"] for r in result]
    assert started_ats == sorted(started_ats, reverse=True)


def test_search_by_type_unknown_returns_empty():
    result = records.search_by_type("unknown_type")  # type: ignore[arg-type]
    assert result == []


# ---------------------------------------------------------------------------
# records.get_resolutions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("incident_type", ["ccu_spike", "queue_stuck", "error_spike", "zone_latency"])
def test_get_resolutions_has_required_fields(incident_type: str):
    result = records.get_resolutions(incident_type)  # type: ignore[arg-type]
    assert len(result) >= 1
    for entry in result:
        for field in ("incident_id", "severity", "title",
                      "root_cause", "resolution_steps", "lessons_learned"):
            assert field in entry


def test_get_resolutions_steps_is_list():
    result = records.get_resolutions("error_spike")
    for entry in result:
        assert isinstance(entry["resolution_steps"], list)
        assert len(entry["resolution_steps"]) >= 1
