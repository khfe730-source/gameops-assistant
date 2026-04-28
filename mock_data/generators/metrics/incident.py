"""Incident scenario generators returning anomalous metric values."""

import hashlib
import random
from datetime import datetime

from mock_data.generators.metrics import normal as metrics_generator


def _make_rng(seed: int, ts: datetime, salt: str) -> random.Random:
    """Create a deterministic RNG using hashlib for cross-process stability."""
    hour_bucket = int(ts.replace(minute=0, second=0, microsecond=0).timestamp())
    key = f"{seed}:{hour_bucket}:{salt}".encode()
    combined = int(hashlib.sha256(key).hexdigest()[:16], 16)
    return random.Random(combined)


def ccu_spike(seed: int, ts: datetime) -> int:
    """Return 3× normal CCU simulating a sudden traffic surge."""
    return metrics_generator.generate_ccu(seed, ts) * 3


def queue_overloaded(seed: int, ts: datetime) -> dict:
    """Return overloaded matchmaking queue under high-CCU scenario."""
    rng = _make_rng(seed, ts, "queue_overloaded")
    ccu = ccu_spike(seed, ts)
    queue_length = int(ccu * rng.uniform(0.15, 0.25))
    avg_wait_seconds = round(rng.uniform(300.0, 600.0), 1)
    return {"queue_length": queue_length, "avg_wait_seconds": avg_wait_seconds}


def queue_stuck(seed: int, ts: datetime) -> dict:
    """Return stuck matchmaking queue simulating a deadlock-like state."""
    rng = _make_rng(seed, ts, "queue_stuck")
    ccu = metrics_generator.generate_ccu(seed, ts)
    # 25–35% of active users stuck in queue, 15–30 min wait
    queue_length = int(ccu * rng.uniform(0.25, 0.35))
    avg_wait_seconds = round(rng.uniform(900.0, 1800.0), 1)
    return {"queue_length": queue_length, "avg_wait_seconds": avg_wait_seconds}


def error_spike(seed: int, ts: datetime) -> dict:
    """Return high error rate simulating a DB outage or critical bug."""
    rng = _make_rng(seed, ts, "err_spike")
    rate_percent = round(rng.uniform(15.0, 30.0), 2)
    total_errors = int(rng.uniform(800, 3000))
    return {"rate_percent": rate_percent, "total_errors": total_errors}


def error_elevated(seed: int, ts: datetime) -> dict:
    """Return moderately elevated error rate under high-CCU scenario."""
    rng = _make_rng(seed, ts, "err_elevated")
    rate_percent = round(rng.uniform(5.0, 12.0), 2)
    total_errors = int(rng.uniform(300, 800))
    return {"rate_percent": rate_percent, "total_errors": total_errors}


def zone_latency_spike(seed: int, ts: datetime) -> dict:
    """Return latency data with ap-northeast-1 severely degraded."""
    result = metrics_generator.generate_latency(seed, ts)
    rng = _make_rng(seed, ts, "zone_lat_spike")
    # ap-northeast-1: network degradation (400–800ms p50, cascading p95/p99)
    p50 = round(rng.uniform(400.0, 800.0), 1)
    p95 = round(p50 * rng.uniform(3.0, 5.0), 1)
    p99 = round(p95 * rng.uniform(2.0, 3.0), 1)
    result["ap-northeast-1"] = {"p50_ms": p50, "p95_ms": p95, "p99_ms": p99}
    return result
