"""Seed-based deterministic game server metrics generator."""

import math
import random
from datetime import datetime


def _make_rng(seed: int, timestamp: datetime, salt: str) -> random.Random:
    """Create a deterministic RNG from seed, timestamp (hour), and salt."""
    hour_bucket = timestamp.replace(minute=0, second=0, microsecond=0).timestamp()
    combined = hash((seed, int(hour_bucket), salt))
    return random.Random(combined)


def generate_ccu(seed: int, timestamp: datetime) -> int:
    """Return simulated concurrent user count."""
    rng = _make_rng(seed, timestamp, "ccu")
    base = 5000
    hour_factor = _hour_weight(timestamp.hour)
    noise = rng.randint(-200, 200)
    return max(0, int(base * hour_factor + noise))


def generate_matchmaking_queue(seed: int, timestamp: datetime) -> dict:
    """Return matchmaking queue depth and average wait time in seconds."""
    rng = _make_rng(seed, timestamp, "mmq")
    ccu = generate_ccu(seed, timestamp)
    queue_ratio = rng.uniform(0.01, 0.05)
    queue_length = int(ccu * queue_ratio)
    avg_wait_seconds = round(rng.uniform(10.0, 120.0), 1)
    return {
        "queue_length": queue_length,
        "avg_wait_seconds": avg_wait_seconds,
    }


def generate_error_rate(seed: int, timestamp: datetime) -> dict:
    """Return error rate percentage and total error count over the last minute."""
    rng = _make_rng(seed, timestamp, "err")
    rate_percent = round(rng.uniform(0.1, 2.0), 2)
    total_errors = int(rng.uniform(5, 200))
    return {
        "rate_percent": rate_percent,
        "total_errors": total_errors,
    }


def generate_latency(seed: int, timestamp: datetime) -> dict:
    """Return p50/p95/p99 latency in milliseconds per server zone."""
    zones = ["ap-northeast-1", "ap-northeast-2", "us-west-2"]
    result: dict[str, dict] = {}
    for zone in zones:
        rng = _make_rng(seed, timestamp, f"lat_{zone}")
        p50 = round(rng.uniform(20.0, 60.0), 1)
        p95 = round(p50 * rng.uniform(1.5, 2.5), 1)
        p99 = round(p95 * rng.uniform(1.2, 2.0), 1)
        result[zone] = {"p50_ms": p50, "p95_ms": p95, "p99_ms": p99}
    return result


def _hour_weight(hour: int) -> float:
    """Return traffic multiplier based on hour of day (peak at 21:00 KST)."""
    peak_hour = 21
    distance = min(abs(hour - peak_hour), 24 - abs(hour - peak_hour))
    return 0.3 + 0.7 * math.exp(-0.07 * distance ** 2)
