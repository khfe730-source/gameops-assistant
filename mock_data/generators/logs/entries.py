"""Deterministic log entry generator for each scenario."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARN", "ERROR"]

_NORMAL_TEMPLATES: list[tuple[str, str, LogLevel]] = [
    ("auth", "User login successful", "INFO"),
    ("auth", "Token refreshed", "INFO"),
    ("auth", "JWT validation passed", "DEBUG"),
    ("auth", "Rate limit check: OK", "DEBUG"),
    ("auth", "Session extended for active user", "INFO"),
    ("matchmaking", "Match created [players=10]", "INFO"),
    ("matchmaking", "Queue depth: 45", "INFO"),
    ("matchmaking", "Match dissolved [reason=player_left]", "WARN"),
    ("matchmaking", "Average wait time: 32s", "INFO"),
    ("matchmaking", "Skill-based bracket assigned", "DEBUG"),
    ("game-session", "Session started", "INFO"),
    ("game-session", "Session ended [duration=1802s]", "INFO"),
    ("game-session", "Player joined session", "DEBUG"),
    ("game-session", "Heartbeat received", "DEBUG"),
    ("api-gateway", "GET /api/v1/health 200 8ms", "INFO"),
    ("api-gateway", "POST /api/v1/match 200 45ms", "INFO"),
    ("api-gateway", "GET /api/v1/user/profile 200 22ms", "INFO"),
    ("api-gateway", "POST /api/v1/auth/login 200 87ms", "INFO"),
    ("user-service", "User profile fetched", "INFO"),
    ("user-service", "Inventory updated", "INFO"),
    ("user-service", "Achievement unlocked", "INFO"),
    ("postgres", "Query executed: SELECT users 12ms", "DEBUG"),
    ("postgres", "Connection pool: 45/100 in use", "INFO"),
    ("redis", "Cache hit: session", "DEBUG"),
    ("redis", "Connection pool: 32/100 in use", "INFO"),
    ("game-server", "Zone ap-northeast-1 p99=45ms", "INFO"),
    ("game-server", "Zone us-west-2 p99=38ms", "INFO"),
    ("game-server", "Zone eu-west-1 p99=52ms", "INFO"),
]

_CCU_SPIKE_TEMPLATES: list[tuple[str, str, LogLevel]] = [
    ("matchmaking", "Queue depth exceeded: 450 > 200", "WARN"),
    ("matchmaking", "Matchmaking timeout: no slot after 300s", "ERROR"),
    ("matchmaking", "Worker thread pool saturated: 100/100", "ERROR"),
    ("matchmaking", "Queue depth critical: 890", "ERROR"),
    ("auth", "Login rate exceeded: 2500 req/s > 1000 limit", "WARN"),
    ("auth", "Connection backlog increasing: 320 pending", "WARN"),
    ("auth", "Login throttle activated", "WARN"),
    ("game-session", "Instance pool near capacity: 92%", "WARN"),
    ("game-session", "Failed to allocate new session: pool full", "ERROR"),
    ("api-gateway", "POST /api/v1/auth/login 503 Service Unavailable", "ERROR"),
    ("api-gateway", "Upstream timeout: matchmaking 15002ms", "ERROR"),
    ("api-gateway", "High error rate detected: 10.2%", "WARN"),
]

_QUEUE_STUCK_TEMPLATES: list[tuple[str, str, LogLevel]] = [
    ("redis", "Connection pool exhausted: 100/100 in use", "ERROR"),
    ("redis", "Connection timeout after 5000ms", "ERROR"),
    ("redis", "Eviction triggered: maxmemory-policy=allkeys-lru", "WARN"),
    ("redis", "Slow response: LPUSH matchmaking:queue 2340ms", "WARN"),
    ("matchmaking", "Redis connection timeout after 5000ms", "ERROR"),
    ("matchmaking", "Queue processing halted: redis unavailable", "ERROR"),
    ("matchmaking", "Worker stalled: waiting for redis lock", "WARN"),
    ("matchmaking", "Average wait time: 1432s — CRITICAL", "ERROR"),
    ("matchmaking", "Dead letter queue growing: 234 entries", "WARN"),
    ("api-gateway", "POST /api/v1/match 503 — matchmaking unavailable", "ERROR"),
    ("api-gateway", "Match request queue timeout: 30002ms", "WARN"),
]

_ERROR_SPIKE_TEMPLATES: list[tuple[str, str, LogLevel]] = [
    ("postgres", "REINDEX TABLE users — table lock acquired", "WARN"),
    ("postgres", "Long-running lock detected: 45s", "WARN"),
    ("postgres", "Query timeout: SELECT * FROM users 30002ms", "ERROR"),
    ("postgres", "Connection pool exhausted: 100/100 in use", "ERROR"),
    ("postgres", "Deadlock detected between sessions 42 and 57", "ERROR"),
    ("user-service", "DB connection timeout: pool wait exceeded 30s", "ERROR"),
    ("user-service", "NullPointerException: user.inventory is null", "ERROR"),
    ("user-service", "DB query failed: Connection refused", "ERROR"),
    ("api-gateway", "Upstream timeout: user-service 30002ms", "ERROR"),
    ("api-gateway", "5xx rate: 250/1000 requests in last minute", "ERROR"),
    ("api-gateway", "POST /api/v1/auth/login 504 Gateway Timeout", "ERROR"),
    ("api-gateway", "Error rate 25.0% — threshold exceeded", "ERROR"),
]

_ZONE_LATENCY_TEMPLATES: list[tuple[str, str, LogLevel]] = [
    ("game-server", "High latency: zone=ap-northeast-1 p99=5200ms", "WARN"),
    ("game-server", "Latency critical: zone=ap-northeast-1 p99=9800ms", "ERROR"),
    ("game-server", "Player disconnect timeout: zone=ap-northeast-1", "ERROR"),
    ("game-server", "Network congestion: zone=ap-northeast-1 packet_loss=12%", "WARN"),
    ("game-server", "Health check failed: zone=ap-northeast-1", "ERROR"),
    ("api-gateway", "Slow upstream: game-server ap-northeast-1 5104ms", "WARN"),
    ("api-gateway", "502 Bad Gateway: game-server ap-northeast-1", "ERROR"),
    ("api-gateway", "Traffic rerouting: ap-northeast-1 → ap-northeast-2", "WARN"),
    ("matchmaking", "Region ap-northeast-1 removed from available pool", "WARN"),
]

_INCIDENT_TEMPLATES: dict[str, list[tuple[str, str, LogLevel]]] = {
    "incident_ccu_spike": _CCU_SPIKE_TEMPLATES,
    "incident_queue_stuck": _QUEUE_STUCK_TEMPLATES,
    "incident_error_spike": _ERROR_SPIKE_TEMPLATES,
    "incident_zone_latency": _ZONE_LATENCY_TEMPLATES,
}

_INCIDENT_RATIO: dict[str, float] = {
    "incident_ccu_spike": 0.40,
    "incident_queue_stuck": 0.45,
    "incident_error_spike": 0.50,
    "incident_zone_latency": 0.35,
}

_ENTRY_COUNT = 200
_WINDOW_MINUTES = 60


def generate_logs(scenario: str, seed: int, now: datetime) -> list[dict]:
    """Generate deterministic log entries spread over the last 60 minutes.

    Args:
        scenario: scenario name (normal | incident_*)
        seed: RNG seed for determinism
        now: reference datetime (UTC)
    """
    rng = random.Random(seed)
    incident_templates = _INCIDENT_TEMPLATES.get(scenario, [])
    incident_ratio = _INCIDENT_RATIO.get(scenario, 0.0)

    entries = []
    for _ in range(_ENTRY_COUNT):
        minutes_ago = rng.uniform(0, _WINDOW_MINUTES)
        ts = now - timedelta(minutes=minutes_ago)

        if incident_templates and rng.random() < incident_ratio:
            service, message, level = rng.choice(incident_templates)
        else:
            service, message, level = rng.choice(_NORMAL_TEMPLATES)

        trace_id = f"tr-{rng.randint(0, 0xFFFFFF):06x}"
        entries.append({
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "level": level,
            "service": service,
            "message": message,
            "trace_id": trace_id,
        })

    return sorted(entries, key=lambda e: e["timestamp"], reverse=True)


def search_logs(
    scenario: str,
    seed: int,
    now: datetime,
    keyword: str = "",
    service: str = "",
    level: str = "",
    minutes: int = 30,
    limit: int = 50,
) -> list[dict]:
    """Return logs matching all given filters within the last `minutes` minutes.

    Args:
        scenario: scenario name
        seed: RNG seed
        now: reference datetime (UTC)
        keyword: case-insensitive substring match on message
        service: exact service name filter
        level: exact log level filter (DEBUG|INFO|WARN|ERROR)
        minutes: time window
        limit: max entries to return
    """
    logs = generate_logs(scenario, seed, now)
    cutoff = now - timedelta(minutes=minutes)

    result = []
    for entry in logs:
        ts = datetime.strptime(entry["timestamp"], "%Y-%m-%dT%H:%M:%S.000Z")
        if ts < cutoff:
            continue
        if keyword and keyword.lower() not in entry["message"].lower():
            continue
        if service and entry["service"] != service:
            continue
        if level and entry["level"] != level:
            continue
        result.append(entry)
        if len(result) >= limit:
            break

    return result


def get_error_logs(
    scenario: str,
    seed: int,
    now: datetime,
    service: str = "",
    minutes: int = 30,
    limit: int = 50,
) -> list[dict]:
    """Return ERROR-level logs within the last `minutes` minutes.

    Args:
        scenario: scenario name
        seed: RNG seed
        now: reference datetime (UTC)
        service: optional service filter
        minutes: time window
        limit: max entries to return
    """
    return search_logs(scenario, seed, now, level="ERROR", service=service, minutes=minutes, limit=limit)


def get_log_stats(
    scenario: str,
    seed: int,
    now: datetime,
    minutes: int = 30,
) -> dict:
    """Return log count statistics by level and by service.

    Args:
        scenario: scenario name
        seed: RNG seed
        now: reference datetime (UTC)
        minutes: time window
    """
    logs = search_logs(scenario, seed, now, minutes=minutes, limit=_ENTRY_COUNT)

    by_level: dict[str, int] = {}
    by_service: dict[str, int] = {}
    for entry in logs:
        by_level[entry["level"]] = by_level.get(entry["level"], 0) + 1
        by_service[entry["service"]] = by_service.get(entry["service"], 0) + 1

    return {
        "total": len(logs),
        "by_level": by_level,
        "by_service": by_service,
        "window_minutes": minutes,
    }


def tail_logs(
    scenario: str,
    seed: int,
    now: datetime,
    service: str = "",
    limit: int = 20,
) -> list[dict]:
    """Return the most recent `limit` log entries, optionally filtered by service.

    Args:
        scenario: scenario name
        seed: RNG seed
        now: reference datetime (UTC)
        service: optional service filter
        limit: max entries to return
    """
    return search_logs(scenario, seed, now, service=service, minutes=_WINDOW_MINUTES, limit=limit)
