# 04. 서브에이전트 & 스킬 패턴

## 개념 정리: 스킬 vs 서브에이전트

이 프로젝트에서 두 개념은 다른 역할을 한다.

| 구분 | 위치 | 역할 | 주체 |
|------|------|------|------|
| **스킬** | `.claude/skills/` | 오케스트레이션 절차서 (단계별 지침) | 메인 Claude |
| **서브에이전트** | `.claude/agents/` | 전문화된 작업자 (단일 역할) | 별도 Claude 인스턴스 |

```
스킬 = "어떤 순서로 누구를 시킬지" 적힌 문서
서브에이전트 = "내가 무슨 일을 하는지" 적힌 문서
```

---

## 서브에이전트 4개

### 1. metrics-analyst

**역할**: 메트릭 4종을 동시 수집하고 이상을 탐지한다.

**핵심 행동**: MCP 툴 4개를 **병렬**로 호출한다.
```
get_ccu_metrics()            ─┐
get_error_rate_metrics()      ├─ 동시 호출
get_latency_metrics()         │
get_matchmaking_queue_metrics()┘
```

**이상 감지 기준**:
| 지표 | 임계값 | 타입 |
|------|--------|------|
| CCU | > 5,000 | `ccu_spike` |
| 에러율 | ≥ 5% | `error_spike` |
| 매치메이킹 대기 | ≥ 300s | `queue_stuck` |
| 존 p99 레이턴시 | ≥ 500ms | `zone_latency` |

**심각도 판정**:
- P1: `error_spike` 포함 OR 이상 3개 이상
- P2: `ccu_spike` 또는 `queue_stuck` 단독
- P3: `zone_latency` 단독
- NORMAL: 이상 없음

**우선순위** (primary_type 결정):
`error_spike` > `ccu_spike` > `queue_stuck` > `zone_latency`

**출력 (JSON만 반환, 설명 텍스트 없음)**:
```json
{
  "timestamp": "2026-05-06T03:08:36Z",
  "anomalies": [
    {"type": "error_spike", "metric": "error_rate_percent", "value": 11.64, "threshold": 5.0, "detail": null}
  ],
  "snapshot": {
    "ccu": 5472,
    "error_rate_percent": 11.64,
    "matchmaking_wait_seconds": 423.9,
    "matchmaking_queue_length": 1320,
    "latency_p99_by_zone": {"ap-northeast-1": 135.0, ...}
  },
  "severity": "P1",
  "primary_type": "error_spike"
}
```

---

### 2. log-investigator

**역할**: 지정된 서비스의 에러 로그를 집중 분석한다.

**입력**: 오케스트레이터가 `service`와 `incident_type`을 프롬프트에 명시한다.

**어떤 서비스를 조사할지는 metrics-analyst가 결정**:
```
ccu_spike / queue_stuck  → matchmaking
error_spike             → api-gateway
zone_latency            → game-server
```

**핵심 행동**: MCP 툴 2개를 **병렬**로 호출한다.
```
get_log_stats(minutes=30)          ─┐
get_error_logs(service, minutes=30) ┘ 동시 호출
```

**상태 판정**:
- 에러 0개: normal
- 에러 1~4개: warning
- 에러 5개 이상: critical

**출력**:
```json
{
  "timestamp": "2026-05-06T03:04:36.000Z",
  "service": "api-gateway",
  "incident_type": "error_spike",
  "window_minutes": 30,
  "error_count": 10,
  "status": "critical",
  "top_errors": [
    {"pattern": "Upstream timeout: matchmaking 15002ms", "count": 6, "latest": "..."}
  ],
  "key_evidence": [
    {"timestamp": "...", "service": "api-gateway", "message": "...", "trace_id": "tr-f8883f"}
  ]
}
```

---

### 3. incident-classifier

**역할**: metrics + log 결과를 종합해 인시던트 타입을 확정하고, 과거 사례에서 해결 방안을 가져온다.

**핵심 행동**: MCP 툴 2개를 **병렬**로 호출한다.
```
search_incidents_by_type(primary_type)  ─┐
get_resolution_steps(primary_type)       ┘ 동시 호출
```

**타입 확정 로직**:
1. `metrics_result.primary_type`을 기준으로 시작
2. `log_result.status == "critical"` 이고 로그가 primary_type과 연관되면 유지
3. 그렇지 않으면 `error_spike`로 상향

**출력**:
```json
{
  "confirmed_type": "error_spike",
  "severity": "P1",
  "resolution_steps": [
    "REINDEX 작업 즉시 중단 (pg_cancel_backend)",
    "장기 락 보유 세션 강제 종료",
    "커넥션 풀 타임아웃 30s → 5s로 단축"
  ],
  "past_incident": {
    "incident_id": "INC-2026-003",
    "title": "에러율 25% 급증 — DB 커넥션 타임아웃",
    "duration_minutes": 45,
    "root_cause": "REINDEX 테이블 락 점유"
  },
  "lessons_learned": "REINDEX CONCURRENTLY 옵션 필수화"
}
```

---

### 4. postmortem-writer

**역할**: 포스트모템 작성에 필요한 데이터를 한 번에 수집한다.

**핵심 행동**: **두 그룹을 병렬**로 실행한다.

```
그룹 A (과거 사례):                그룹 B (현재 상태):
search_incidents_by_type()  ─┐    get_ccu_metrics()         ─┐
get_resolution_steps()       ┘    get_error_rate_metrics()    │
                                   get_latency_metrics()       │ 동시
                                   get_matchmaking_queue_metrics()┘
```

**회복 확인**: 모든 지표가 정상 범위 내인지 판단한다.
- CCU ≤ 5000 AND 에러율 < 1% AND 큐 대기 < 60s AND p99 < 200ms → `all_normal: true`

**출력**:
```json
{
  "current_metrics": {
    "ccu": 5001,
    "error_rate_percent": 0.16,
    "all_normal": true,
    ...
  },
  "past_incidents": [...],
  "resolution_steps": [...],
  "lessons_learned": "...",
  "affected_services": ["api-gateway", "matchmaking"]
}
```

---

## 스킬 2개

### 1. incident-response

**파일**: `.claude/skills/incident-response/SKILL.md`

**4단계 파이프라인**:

```
Step 1: metrics-analyst 호출
  ↓ primary_type 추출
  ↓ null이면 → "정상" 요약 출력 후 종료

Step 2: primary_type → 서비스 결정
  ccu_spike / queue_stuck → matchmaking
  error_spike             → api-gateway
  zone_latency            → game-server
  → log-investigator 호출

Step 3: incident-classifier 호출
  metrics JSON + log JSON 전달

Step 4: 진단 리포트 출력 (마크다운 표)
```

**리포트 출력 포맷** (고정):
```markdown
## 인시던트 진단 리포트
**진단 시각**: ...  **확정 타입**: ...  **심각도**: P1/P2/P3

### 현재 지표 스냅샷
| 지표 | 현재값 | 정상 범위 | 상태 |

### 이상 감지 항목
### 근거 로그
### 즉각 대응 방안
### 과거 사례 교훈
### 모니터링 포인트
```

---

### 2. postmortem

**파일**: `.claude/skills/postmortem/SKILL.md`

**3단계**:

```
Step 1: 컨텍스트 수집
  - 이전 /incident-response 결과 or 사용자 입력에서:
    incident_type, 시작 시각, 최고 수치, 종료 시각, 적용한 조치

Step 2: postmortem-writer 서브에이전트 호출
  - 과거 사례 + 현재 지표 동시 수집

Step 3: 포스트모템 문서 생성
  - 7개 섹션 마크다운 문서
  - all_normal=false이면 경고 배너 표시
  - 저장 제안: postmortems/YYYY-MM-DD_<type>.md
```

**생성 문서 섹션**:
1. 요약 (Executive Summary)
2. 타임라인
3. 영향 범위
4. 근본 원인
5. 해결 과정
6. 재발 방지 액션 아이템
7. 현재 지표 (해소 확인)

---

## 서브에이전트 파일 구조

`.claude/agents/metrics-analyst.md` 예시:

```markdown
---
name: metrics-analyst
description: 게임 서버 메트릭 전문 분석 에이전트...
tools:
  - mcp__metrics__get_ccu_metrics
  - mcp__metrics__get_error_rate_metrics
  ...
---

# 역할
...

# 입력
...

# 처리 절차
1. 4개 MCP 툴 동시 호출
2. 이상 감지
...

# 출력 스키마
```json
{...}
```

# 중요 제약
- JSON 블록만 반환, 설명 텍스트 없음
```

**핵심**: `tools:` 목록에 있는 MCP 툴만 호출할 수 있다.
서브에이전트는 자신의 역할에 필요한 툴만 알고 있다.

---

## 오케스트레이션 패턴의 핵심 원리

### 컨텍스트 격리

```
메인 Claude (오케스트레이터)
  ↓ 프롬프트 전송
  서브에이전트 (격리된 컨텍스트)
    - 4개 툴 호출 → 수백 줄 원시 데이터
    - → JSON 요약으로 압축
  ↑ JSON 요약만 반환
메인 Claude
  - 원시 데이터 보지 않음, 요약만 봄
```

**왜 중요한가?** 메트릭 4개 + 로그 200개를 메인 컨텍스트에 직접 쏟으면
토큰 사용량이 폭발하고 응답 품질이 낮아진다.
서브에이전트가 압축 + 요약을 담당해 메인 컨텍스트를 보호한다.

### 단방향 JSON 계약

서브에이전트 간 데이터 교환은 **JSON 스키마로 고정**된다.
메시지 구조가 바뀌면 다음 서브에이전트가 파싱하지 못하므로,
각 에이전트 파일에 출력 스키마가 명시적으로 정의되어 있다.

### 병렬 실행

같은 서브에이전트 내에서 독립적인 MCP 툴 호출은 모두 병렬로 수행한다.
`postmortem-writer`는 "과거 사례 조회(2개 툴)"와 "현재 지표 확인(4개 툴)"을
동시에 실행해 대기 시간을 절반으로 줄인다.

---

## 다음으로 읽을 문서

- 이 시스템이 어떻게 테스트되는지 → [05-testing.md](05-testing.md)
