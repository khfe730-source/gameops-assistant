# 05. 테스트 전략

## 전체 현황

```
tests/
├── test_metrics_generator.py    14 케이스  — 메트릭 생성기 단위 테스트
├── test_scenarios.py            22 케이스  — 시나리오 파사드 + 장애 변형
├── test_incident_db.py          18 케이스  — 인시던트 DB CRUD + 검색
├── test_log_search.py           35 케이스  — 로그 생성 + 필터링
└── test_mcp_integration.py      32 케이스  — MCP 서버 통합 테스트
                                 ─────────
                                 121 케이스 합계
```

테스트 실행:
```bash
uv run pytest tests/ -v
```

---

## test_metrics_generator.py (14개)

### 무엇을 테스트하나

`generators/metrics/normal.py`의 생성 함수들을 직접 호출해
출력값이 예상 범위 내에 있는지 검증한다.

### 주요 패턴

**형태 검증** (필수 키가 존재하는가):
```python
def test_queue_shape(self):
    result = generate_matchmaking_queue(seed=42, ts=TS)
    assert "queue_length" in result and "avg_wait_seconds" in result
```

**범위 검증** (값이 합리적 범위인가):
```python
def test_latency_p99_below_200ms(self):
    zones = generate_latency(seed=42, ts=TS)
    for zone in zones.values():
        assert zone["p99_ms"] < 200.0
```

**순서 보장** (p50 ≤ p95 ≤ p99):
```python
def test_latency_percentile_order(self):
    zones = generate_latency(seed=42, ts=TS)
    for zone in zones.values():
        assert zone["p50_ms"] <= zone["p95_ms"] <= zone["p99_ms"]
```

**결정론** (같은 입력 → 같은 출력):
```python
def test_deterministic(self):
    a = generate_ccu(seed=42, ts=TS)
    b = generate_ccu(seed=42, ts=TS)
    assert a == b
```

---

## test_scenarios.py (22개)

### 무엇을 테스트하나

`mock_data/scenarios.py` 파사드와 장애 시나리오별 수치가
기대한 임계값을 충족하는지 검증한다.

### 시나리오별 검증 예시

```python
class TestIncidentCcuSpike:
    def test_ccu_is_3x_normal(self):
        spike = get_ccu(Scenario.INCIDENT_CCU_SPIKE, SEED, TS)
        normal = get_ccu(Scenario.NORMAL, SEED, TS)
        assert spike == normal * 3          # 정확히 3배

    def test_queue_wait_above_300s(self):
        assert get_matchmaking_queue(Scenario.INCIDENT_CCU_SPIKE, SEED, TS)["avg_wait_seconds"] >= 300.0

class TestIncidentQueueStuck:
    def test_ccu_unchanged(self):
        # queue_stuck은 CCU에 영향 없어야 함
        assert get_ccu(Scenario.INCIDENT_QUEUE_STUCK, SEED, TS) == get_ccu(Scenario.NORMAL, SEED, TS)

    def test_queue_wait_above_900s(self):
        assert get_matchmaking_queue(Scenario.INCIDENT_QUEUE_STUCK, SEED, TS)["avg_wait_seconds"] >= 900.0
```

**설계 의도**: 각 장애 시나리오가 "이 수치는 올라가고, 저 수치는 정상"이라는
명확한 시그니처를 가지는지 검증한다. 이게 없으면 AI가 시나리오를 잘못 분류할 수 있다.

### 픽스처 회귀 테스트

```python
class TestFixtures:
    def test_fixture_matches_generator(self):
        for scenario in Scenario:
            fixture = json.load(open(f"fixtures/{scenario.value}.json"))
            live = get_all_metrics(scenario, SEED, TS)
            assert fixture["ccu"] == live["ccu"]
            assert fixture["error_rate"] == live["error_rate"]
```

생성기 코드를 수정했을 때 이 테스트가 실패하면 **의도치 않게 수치가 바뀐 것**.
픽스처 파일을 의도적으로 업데이트해야 한다.

---

## test_incident_db.py (18개)

### 무엇을 테스트하나

`generators/incident_db/records.py`의 쿼리 함수들.

```python
class TestListRecent:
    def test_returns_incidents_in_window(self):
        result = list_recent(hours=720)  # 30일
        assert len(result) > 0

    def test_newest_first(self):
        incidents = list_recent(hours=9999)
        dates = [i["started_at"] for i in incidents]
        assert dates == sorted(dates, reverse=True)

class TestSearchByType:
    def test_returns_only_matching_type(self):
        results = search_by_type(IncidentType.CCU_SPIKE)
        assert all(r["type"] == "ccu_spike" for r in results)

class TestGetResolutions:
    def test_has_resolution_steps(self):
        resolutions = get_resolutions(IncidentType.ERROR_SPIKE)
        for r in resolutions:
            assert len(r["resolution_steps"]) > 0
```

---

## test_log_search.py (35개)

### 무엇을 테스트하나

`generators/logs/entries.py`의 생성·필터링 함수들.

### 핵심 케이스들

**시나리오별 에러 수 차이**:
```python
def test_incident_has_more_errors_than_normal(self):
    normal = generate_logs(Scenario.NORMAL, SEED, NOW)
    spike = generate_logs(Scenario.INCIDENT_ERROR_SPIKE, SEED, NOW)
    
    normal_errors = [l for l in normal if l["level"] == "ERROR"]
    spike_errors = [l for l in spike if l["level"] == "ERROR"]
    
    assert len(spike_errors) > len(normal_errors)
```

**필터링 정확도**:
```python
def test_service_filter(self):
    logs = search_logs(Scenario.NORMAL, SEED, NOW, service="matchmaking")
    assert all(l["service"] == "matchmaking" for l in logs)

def test_keyword_filter(self):
    logs = search_logs(Scenario.NORMAL, SEED, NOW, keyword="timeout")
    assert all("timeout" in l["message"].lower() for l in logs)

def test_time_window(self):
    logs = search_logs(Scenario.NORMAL, SEED, NOW, minutes=5)
    cutoff = NOW - timedelta(minutes=5)
    for log in logs:
        ts = datetime.fromisoformat(log["timestamp"])
        assert ts >= cutoff
```

**집계 통계**:
```python
def test_stats_levels_sum_to_total(self):
    stats = get_log_stats(Scenario.NORMAL, SEED, NOW)
    level_sum = sum(stats["by_level"].values())
    assert level_sum == stats["total"]
```

---

## test_mcp_integration.py (32개)

### 무엇을 테스트하나

MCP 서버의 툴 함수들을 **실제 HTTP/stdio 없이** 직접 임포트해서 호출한다.
`mock_data` 파이프라인 전체가 MCP 레이어와 연결되는지 검증한다.

### 구조

```python
# MCP 서버 함수를 직접 임포트
from mcp_servers.metrics_server import get_ccu_metrics, get_error_rate_metrics
from mcp_servers.log_search_server import get_error_logs, get_log_stats
from mcp_servers.incident_db_server import search_incidents_by_type
```

### 시나리오별 신호 검증

각 장애 시나리오에서 AI가 올바른 판단을 내릴 수 있는 신호가
실제로 나오는지 검증한다.

```python
class TestErrorSpikeScenario:
    def setup_method(self):
        # 환경변수 설정 (서버가 이 시나리오로 동작하도록)
        os.environ["METRICS_SCENARIO"] = "incident_error_spike"
        os.environ["LOG_SCENARIO"] = "incident_error_spike"
    
    def test_error_rate_above_threshold(self):
        result = get_error_rate_metrics()
        assert result["rate_percent"] >= 5.0  # AI가 이상 감지해야 함
    
    def test_error_logs_contain_incident_patterns(self):
        result = get_error_logs(service="api-gateway")
        messages = [l["message"] for l in result["logs"]]
        # 적어도 하나의 장애 관련 메시지가 있어야 함
        assert any("timeout" in m.lower() or "error" in m.lower() for m in messages)
```

**왜 중요한가?** 단위 테스트는 각 레이어를 개별 검증하지만,
통합 테스트는 "전체 파이프라인이 AI에게 올바른 신호를 주는가"를 검증한다.
AI가 `error_spike` 시나리오에서 `error_spike`를 감지하지 못하면
시스템 전체가 무의미해진다.

---

## 테스트 설계 원칙

### 1. 결정론적 테스트

모든 테스트는 `seed=42`, 고정 타임스탬프를 사용한다.
랜덤 시드가 없으면 테스트가 실행할 때마다 다른 결과가 나온다.

```python
SEED = 42
TS = datetime(2026, 4, 29, 21, 0, 0)  # 항상 동일한 시간
```

### 2. 장애 시그니처 명시

"에러율이 높다"가 아니라 **"어떤 임계값을 넘는가"**를 검증한다.
AI의 이상 감지 임계값과 테스트 임계값을 일치시켜야
AI가 감지할 수 없는 신호를 테스트가 통과시키는 일이 없다.

```python
# 나쁜 예: "정상보다 높다"는 것만 검증
assert spike_errors > normal_errors

# 좋은 예: AI의 임계값 기준으로 검증
assert get_error_rate_metrics()["rate_percent"] >= 5.0  # metrics-analyst의 임계값
```

### 3. 레이어별 테스트

```
unit(generators) → unit(scenarios facade) → unit(db/log queries) → integration(mcp)
```

각 레이어가 독립적으로 검증되므로 버그 위치를 빠르게 찾을 수 있다.
통합 테스트가 실패해도 어느 레이어 문제인지 단위 테스트로 좁힐 수 있다.
