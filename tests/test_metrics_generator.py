"""Tests for mock_data.generators.metrics.normal."""

from datetime import datetime

from mock_data.generators.metrics.normal import (
    generate_ccu,
    generate_error_rate,
    generate_latency,
    generate_matchmaking_queue,
)

SEED = 42
TS = datetime(2026, 4, 29, 21, 0, 0)  # peak hour


class TestGenerateCcu:
    def test_returns_positive_int(self):
        assert generate_ccu(SEED, TS) > 0

    def test_deterministic(self):
        assert generate_ccu(SEED, TS) == generate_ccu(SEED, TS)

    def test_different_seed_gives_different_value(self):
        assert generate_ccu(SEED, TS) != generate_ccu(SEED + 1, TS)


class TestGenerateMatchmakingQueue:
    def test_returns_required_keys(self):
        result = generate_matchmaking_queue(SEED, TS)
        assert "queue_length" in result
        assert "avg_wait_seconds" in result

    def test_queue_length_positive(self):
        assert generate_matchmaking_queue(SEED, TS)["queue_length"] >= 0

    def test_avg_wait_positive(self):
        assert generate_matchmaking_queue(SEED, TS)["avg_wait_seconds"] > 0

    def test_deterministic(self):
        assert generate_matchmaking_queue(SEED, TS) == generate_matchmaking_queue(SEED, TS)


class TestGenerateErrorRate:
    def test_returns_required_keys(self):
        result = generate_error_rate(SEED, TS)
        assert "rate_percent" in result
        assert "total_errors" in result

    def test_rate_in_valid_range(self):
        rate = generate_error_rate(SEED, TS)["rate_percent"]
        assert 0.0 <= rate <= 100.0

    def test_deterministic(self):
        assert generate_error_rate(SEED, TS) == generate_error_rate(SEED, TS)


class TestGenerateLatency:
    ZONES = ["ap-northeast-1", "ap-northeast-2", "us-west-2"]

    def test_returns_all_zones(self):
        result = generate_latency(SEED, TS)
        for zone in self.ZONES:
            assert zone in result

    def test_each_zone_has_percentiles(self):
        result = generate_latency(SEED, TS)
        for zone in self.ZONES:
            assert "p50_ms" in result[zone]
            assert "p95_ms" in result[zone]
            assert "p99_ms" in result[zone]

    def test_percentile_order(self):
        result = generate_latency(SEED, TS)
        for zone in self.ZONES:
            z = result[zone]
            assert z["p50_ms"] <= z["p95_ms"] <= z["p99_ms"]

    def test_deterministic(self):
        assert generate_latency(SEED, TS) == generate_latency(SEED, TS)
