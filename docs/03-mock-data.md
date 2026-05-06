# 03. Mock Data 구조 분석

## 전체 구조

```
mock_data/
├── scenarios.py           ← 파사드 (외부에서 유일하게 사용하는 진입점)
├── generators/
│   ├── metrics/
│   │   ├── normal.py      ← 정상 상태 메트릭 생성기
│   │   └── incident.py    ← 장애 상태 메트릭 변형기
│   ├── incident_db/
│   │   └── records.py     ← 정적 인시던트 레코드 12개
│   └── logs/
│       └── entries.py     ← 로그 엔트리 생성기
└── fixtures/
    ├── normal.json
    ├── incident_ccu_spike.json
    ├── incident_queue_stuck.json
    ├── incident_error_spike.json
    └── incident_zone_latency.json
```

---

## scenarios.py — 파사드 패턴

MCP 서버가 `mock_data`를 사용할 때 항상 `scenarios.py`를 통해 접근한다.
내부 생성기가 어떻게 구현됐는지 알 필요 없이 시나리오 이름만 전달하면 된다.

```python
from mock_data.scenarios import Scenario, get_all_metrics

# 사용 예시
result = get_all_metrics(Scenario.INCIDENT_ERROR_SPIKE, seed=42, ts=datetime.now())
```

### Scenario enum
```python
class Scenario(str, Enum):
    NORMAL               = "normal"
    INCIDENT_CCU_SPIKE   = "incident_ccu_spike"
    INCIDENT_QUEUE_STUCK = "incident_queue_stuck"
    INCIDENT_ERROR_SPIKE = "incident_error_spike"
    INCIDENT_ZONE_LATENCY = "incident_zone_latency"
```

`str`을 상속하므로 `Scenario.NORMAL == "normal"` 비교가 가능하고,
환경변수에서 직접 변환도 된다: `Scenario(os.environ.get("METRICS_SCENARIO", "normal"))`.

### 파사드 함수
```python
get_ccu(scenario, seed, ts) -> int
get_matchmaking_queue(scenario, seed, ts) -> dict
get_error_rate(scenario, seed, ts) -> dict
get_latency(scenario, seed, ts) -> dict
get_all_metrics(scenario, seed, ts) -> dict  # 위 4개 묶음
```

내부에서 `match scenario:` 분기로 올바른 생성기를 라우팅한다.

---

## generators/metrics/normal.py — 결정론적 RNG

### 핵심: `_make_rng(seed, timestamp, salt)`

**문제**: 단순히 `random.random()`을 쓰면 테스트마다 값이 달라진다.
`random.seed(42)` 를 쓰면 프로세스 간 상태가 공유되지 않아 결과가 다를 수 있다.

**해결**: `hashlib.sha256`으로 결정론적 난수를 생성한다.

```python
def _make_rng(seed: int, timestamp: datetime, salt: str) -> random.Random:
    hour_bucket = timestamp.replace(minute=0, second=0, microsecond=0)
    key = f"{seed}:{hour_bucket.isoformat()}:{salt}"
    digest = hashlib.sha256(key.encode()).hexdigest()
    rng_seed = int(digest[:16], 16)
    return random.Random(rng_seed)
```

- **`seed`**: 호출자가 제공 (MCP 서버는 현재 타임스탬프를 seed로 씀)
- **`hour_bucket`**: 같은 시간대 내에서는 항상 동일한 값 (시간 단위로 값이 바뀜)
- **`salt`**: 지표별로 다른 값 ("ccu", "mmq", "err", "lat_ap-northeast-1" 등)

결과: **같은 시나리오를 같은 시간에 여러 번 호출하면 항상 같은 수치가 나온다**.
(테스트에서 `seed=42`, `ts=datetime(2026, 4, 29, 21, 0, 0)`으로 고정하는 이유)

### 메트릭 생성 로직

**CCU**
```python
def generate_ccu(seed, ts) -> int:
    rng = _make_rng(seed, ts, "ccu")
    base = 5000
    hour_weight = _hour_weight(ts.hour)  # 새벽=0.3, 저녁 9시=1.0
    noise = rng.randint(-200, 200)
    return int(base * hour_weight + noise)
```

**레이턴시** — p50 < p95 < p99 순서를 보장하는 방법:
```python
p50 = rng.uniform(20, 60)
p95 = p50 * rng.uniform(1.5, 2.5)   # p50보다 항상 큼
p99 = p95 * rng.uniform(1.2, 2.0)   # p95보다 항상 큼
```

---

## generators/metrics/incident.py — 장애 변형

정상 생성기 값을 기반으로 장애 수치를 만든다.

```python
def ccu_spike(seed, ts) -> int:
    normal = generate_ccu(seed, ts)
    return normal * 3                  # 3배 폭증

def queue_stuck(seed, ts) -> dict:
    return {
        "queue_length": int(generate_ccu(seed, ts) * rng.uniform(0.25, 0.35)),
        "avg_wait_seconds": rng.uniform(900, 1800)  # 15~30분 대기
    }

def error_spike(seed, ts) -> dict:
    return {
        "rate_percent": rng.uniform(15, 30),
        "total_errors": rng.randint(800, 3000)
    }

def zone_latency_spike(seed, ts) -> dict:
    # ap-northeast-1만 이상, 나머지는 정상
    normal = generate_latency(seed, ts)
    normal["ap-northeast-1"] = {
        "p50_ms": rng.uniform(400, 800),
        "p95_ms": rng.uniform(1200, 3000),
        "p99_ms": rng.uniform(2400, 6000)
    }
    return normal
```

---

## generators/logs/entries.py — 로그 생성

### 구조

200개 로그 엔트리를 60분 윈도우에 걸쳐 생성한다.

```python
def generate_logs(scenario, seed, now) -> list[dict]:
    rng = random.Random(seed)
    # 시나리오에 따라 템플릿 풀 결정
    if scenario == Scenario.NORMAL:
        templates = _NORMAL_TEMPLATES
    else:
        incident_ratio = 0.35  # 35~50%는 장애 로그
        templates = incident_templates + normal_templates
    
    entries = []
    for i in range(200):
        template = rng.choice(templates)
        timestamp = now - timedelta(seconds=rng.randint(0, 3600))
        entries.append({
            "timestamp": timestamp.isoformat(),
            "level": template["level"],
            "service": template["service"],
            "message": template["message"],
            "trace_id": f"tr-{rng.randint(0, 0xFFFFFF):06x}"
        })
    
    return sorted(entries, key=lambda x: x["timestamp"], reverse=True)
```

### 템플릿 풀

**정상 (40개)**:
- `auth` 서비스: 로그인 성공, JWT 검증, 토큰 갱신
- `matchmaking`: 매치 생성, 큐 깊이 보고, 매치 해소
- `api-gateway`: 200 응답, 레이턴시 메트릭
- `postgres`: 쿼리 실행, 커넥션 풀 통계
- 기타 서비스들

**장애별 (각 9~12개)**:

| 시나리오 | 주요 템플릿 예시 |
|---------|----------------|
| `ccu_spike` | "Queue depth exceeded: 450 > 200", "Matchmaking timeout after 300s" |
| `queue_stuck` | "Redis connection pool exhausted", "Queue processing halted" |
| `error_spike` | "REINDEX holding lock on table sessions", "Connection pool exhausted" |
| `zone_latency` | "Latency critical: ap-northeast-1 p99=5200ms", "Health check failed" |

---

## generators/incident_db/records.py — 정적 레코드

메트릭·로그 생성기와 달리 이 파일은 **완전히 정적**이다.
12개 인시던트 딕셔너리를 하드코딩해 두고, 쿼리 함수로 필터링한다.

```python
_RECORDS: list[dict] = [
    {
        "incident_id": "INC-2026-001",
        "type": "ccu_spike",
        "severity": "P1",
        "title": "v2.3.0 패치 후 동접 3배 폭증",
        "started_at": "2026-03-15T14:00:00",
        ...
    },
    # ... 11개 더
]

def list_recent(hours=24) -> list[dict]: ...
def get_by_id(incident_id) -> dict | None: ...
def search_by_type(incident_type) -> list[dict]: ...
def get_resolutions(incident_type) -> list[dict]: ...
```

**왜 정적인가?** 인시던트 DB는 "과거에 있었던 일"이므로 시나리오와 무관하게
항상 동일한 데이터를 반환하는 것이 자연스럽다.
메트릭/로그는 "지금 이 순간"이라서 시나리오에 따라 달라진다.

---

## fixtures/ — 골든 스냅샷

5개 시나리오 × 4개 메트릭 = 기준 스냅샷을 JSON으로 저장한 것.

**생성 조건**: `seed=42`, `ts=2026-04-29T21:00:00`

**사용 목적**: 회귀 테스트.
생성기 코드를 수정했을 때 `test_fixture_matches_generator` 테스트가 실패하면
의도치 않게 수치가 바뀐 것이다.

```python
# tests/test_scenarios.py
def test_fixture_matches_generator(self):
    for scenario in Scenario:
        fixture = json.load(open(f"fixtures/{scenario.value}.json"))
        live = get_all_metrics(scenario, seed=42, ts=TS)
        assert fixture["ccu"] == live["ccu"]  # 수치가 바뀌면 실패
```

---

## 다음으로 읽을 문서

- AI 에이전트가 어떻게 이 데이터를 활용하는지 → [04-agents-skills.md](04-agents-skills.md)
