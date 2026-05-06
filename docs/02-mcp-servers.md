# 02. MCP 서버 상세 분석

## MCP가 뭔지 먼저

MCP(Model Context Protocol)는 AI 모델이 외부 시스템을 호출하는 표준 인터페이스다.
Claude Code에서 `mcp__서버명__툴명()` 형태로 함수처럼 호출한다.

```
Claude Code  →  (stdio)  →  MCP 서버 프로세스  →  데이터 반환
```

이 프로젝트에서는 **FastMCP** 라이브러리로 서버를 구현했다.
FastMCP는 Python 함수에 `@mcp.tool()` 데코레이터를 붙이면 MCP 툴이 된다.

```python
# FastMCP 패턴
mcp = FastMCP("서버이름")

@mcp.tool()
def get_ccu_metrics() -> dict:
    """CCU 메트릭 반환"""
    return {...}

if __name__ == "__main__":
    mcp.run()   # stdio로 실행
```

---

## 서버 등록 방법 (.mcp.json)

```json
{
  "mcpServers": {
    "metrics": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_servers.metrics_server"],
      "env": {"METRICS_SCENARIO": "incident_ccu_spike"}
    },
    "incident_db": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_servers.incident_db_server"]
    },
    "log_search": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_servers.log_search_server"],
      "env": {"LOG_SCENARIO": "incident_ccu_spike"}
    }
  }
}
```

- `command` + `args`: 서버를 실행하는 셸 명령어
- `env`: 서버에 전달할 환경변수 (시나리오 제어에 사용)
- Claude Code 시작 시 3개 서버가 별도 프로세스로 뜬다

**중요**: MCP 서버는 stdio로 통신하므로 `print()` 사용 금지.
로그는 반드시 `logging` + `stderr`로 출력해야 한다.

---

## 1. metrics_server.py

### 역할
CCU, 매치메이킹 큐, 에러율, 레이턴시 메트릭을 반환하는 서버.
실제 시스템에서는 Datadog / Prometheus 역할.

### 시나리오 제어
```bash
METRICS_SCENARIO=incident_error_spike  # 환경변수로 시나리오 전환
```

### 툴 4개

**`get_ccu_metrics()`**
```json
{
  "ccu": 5472,
  "scenario": "incident_error_spike",
  "timestamp": "2026-05-06T03:08:36"
}
```

**`get_matchmaking_queue_metrics()`**
```json
{
  "queue_length": 1320,
  "avg_wait_seconds": 423.9,
  "scenario": "incident_error_spike",
  "timestamp": "2026-05-06T03:08:36"
}
```

**`get_error_rate_metrics()`**
```json
{
  "rate_percent": 11.64,
  "total_errors": 980,
  "scenario": "incident_error_spike",
  "timestamp": "2026-05-06T03:08:36"
}
```

**`get_latency_metrics()`**
```json
{
  "zones": {
    "ap-northeast-1": {"p50_ms": 28.2, "p95_ms": 53.5, "p99_ms": 135.0},
    "ap-northeast-2": {"p50_ms": 30.7, "p95_ms": 72.2, "p99_ms": 109.6},
    "us-west-2":      {"p50_ms": 55.5, "p95_ms": 136.3, "p99_ms": 87.1}
  },
  "scenario": "incident_error_spike",
  "timestamp": "2026-05-06T03:08:36"
}
```

### 서버 코드 구조 요약
```python
SCENARIO = Scenario(os.environ.get("METRICS_SCENARIO", "normal"))

@mcp.tool()
def get_ccu_metrics() -> dict:
    seed = int(datetime.now().timestamp())
    ts = datetime.now()
    return {
        "ccu": get_ccu(SCENARIO, seed, ts),   # mock_data.scenarios 호출
        "scenario": SCENARIO.value,
        "timestamp": ts.isoformat()
    }
```

### 시나리오별 예상 수치

| 시나리오 | CCU | 에러율 | 큐 대기 | 레이턴시 p99 |
|---------|-----|--------|---------|------------|
| normal | ~5000 | <2% | <120s | <200ms |
| ccu_spike | ~15000 | ~10% | ~350s | 정상 |
| queue_stuck | ~5000 | 정상 | >900s | 정상 |
| error_spike | ~5000 | >15% | 상승 | 정상 |
| zone_latency | ~5000 | 정상 | 정상 | ap-ne-1 >5000ms |

---

## 2. incident_db_server.py

### 역할
과거 인시던트 기록을 조회하는 서버.
실제 시스템에서는 Confluence / JIRA / 사내 장애 DB 역할.

### 특징
- 시나리오 환경변수 없음 (데이터가 정적이기 때문)
- 12개의 정적 레코드 (2025~2026년 실제 장애처럼 작성)

### 툴 4개

**`list_recent_incidents(hours=24)`**
- 지난 N시간 내 인시던트 목록
- 반환: `{"incidents": [...], "count": int}`

**`get_incident(incident_id)`**
- 특정 인시던트 상세 조회
- 예: `get_incident("INC-2026-003")`

**`search_incidents_by_type(incident_type)`**
- 타입별 조회: `ccu_spike` | `queue_stuck` | `error_spike` | `zone_latency`
- 최신순 정렬

**`get_resolution_steps(incident_type)`**
- 해결 방안 조회 (인시던트 분류에서 핵심 사용)
- 반환 구조:
```json
{
  "resolutions": [
    {
      "incident_id": "INC-2026-003",
      "severity": "P1",
      "title": "에러율 25% 급증 — DB 커넥션 타임아웃",
      "root_cause": "REINDEX 작업이 테이블 락 점유",
      "resolution_steps": [
        "REINDEX 작업 즉시 중단 (pg_cancel_backend)",
        "장기 락 보유 세션 강제 종료",
        "커넥션 풀 타임아웃 30s → 5s로 단축"
      ],
      "lessons_learned": "REINDEX CONCURRENTLY 옵션 필수화"
    }
  ],
  "count": 2
}
```

### 인시던트 레코드 구조
```python
{
    "incident_id": "INC-2026-001",
    "type": "ccu_spike",
    "severity": "P1",
    "title": "v2.3.0 패치 후 동접 3배 폭증",
    "started_at": "2026-03-15T14:00:00",
    "resolved_at": "2026-03-15T15:45:00",
    "duration_minutes": 105,
    "affected_components": ["matchmaking", "api-gateway", "auth"],
    "summary": "...",
    "root_cause": "...",
    "resolution_steps": ["..."],
    "lessons_learned": "..."
}
```

---

## 3. log_search_server.py

### 역할
게임 서버 로그를 검색하는 서버.
실제 시스템에서는 Loki / Elasticsearch / CloudWatch Logs 역할.

### 시나리오 제어
```bash
LOG_SCENARIO=incident_queue_stuck
```

### 툴 4개

**`search_logs(keyword, service, level, minutes, limit)`**
- 4개 필터 AND 조건
- `service`: auth | matchmaking | game-session | api-gateway | user-service | postgres | redis | game-server
- `level`: DEBUG | INFO | WARN | ERROR

**`get_error_logs(service, minutes, limit)`**
- `search_logs(level="ERROR", ...)`의 단축형

**`get_log_stats(minutes)`**
- 로그 집계 뷰
```json
{
  "total": 200,
  "by_level": {"DEBUG": 30, "INFO": 120, "WARN": 20, "ERROR": 30},
  "by_service": {"api-gateway": 40, "matchmaking": 35, ...},
  "window_minutes": 30,
  "scenario": "incident_error_spike"
}
```

**`tail_logs(service, limit)`**
- 가장 최근 N개 로그

### 로그 엔트리 구조
```json
{
  "timestamp": "2026-05-06T03:04:36.000Z",
  "level": "ERROR",
  "service": "api-gateway",
  "message": "Upstream timeout: matchmaking 15002ms",
  "trace_id": "tr-f8883f"
}
```

---

## 자동 허용 설정 (.claude/settings.local.json)

매번 MCP 툴 호출 시 사용자 승인을 요청하면 인시던트 대응이 너무 느려진다.
그래서 자주 쓰는 툴들을 미리 허용 목록에 등록해 두었다.

```json
{
  "permissions": {
    "allow": [
      "mcp__metrics__get_ccu_metrics",
      "mcp__metrics__get_error_rate_metrics",
      "mcp__metrics__get_latency_metrics",
      "mcp__metrics__get_matchmaking_queue_metrics",
      "mcp__log_search__get_log_stats",
      "mcp__log_search__get_error_logs",
      "mcp__log_search__search_logs",
      "mcp__incident_db__search_incidents_by_type",
      "mcp__incident_db__get_resolution_steps"
    ]
  }
}
```

---

## 다음으로 읽을 문서

- 모킹 데이터가 어떻게 만들어지는지 → [03-mock-data.md](03-mock-data.md)
