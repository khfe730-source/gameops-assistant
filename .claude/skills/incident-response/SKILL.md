---
name: incident-response
description: Game server incident diagnosis and response. Use this skill whenever the user reports or suspects a server problem — slow matchmaking, high error rates, lag spikes, CCU anomalies, queue backlogs, zone latency, or any "something feels wrong" signal. Also trigger when the user asks to check server health, investigate an alert, or diagnose unusual metrics. When in doubt, use this skill.
---

# 인시던트 대응 절차

게임 서버 장애를 진단하고 즉각 대응 방안을 도출하는 절차.

## Step 1: 현황 수집

다음 6개 툴을 **모두 동시에** 호출해 현재 상태 스냅샷을 확보한다.

메트릭 (metrics MCP):
- `get_ccu_metrics`
- `get_error_rate_metrics`
- `get_latency_metrics`
- `get_matchmaking_queue_metrics`

로그 (log_search MCP):
- `get_log_stats(minutes=30)`
- `get_error_logs(minutes=30, limit=20)`

## Step 2: 이상 감지

수집된 데이터에서 아래 기준으로 이상 항목을 식별한다.

| 지표 | 이상 기준 | 의심 타입 |
|------|----------|----------|
| CCU | 5,000 초과 또는 직전 대비 2× 이상 | `ccu_spike` |
| 에러율 | ≥ 5% | `error_spike` |
| 매치메이킹 대기 시간 | ≥ 300s | `queue_stuck` |
| 특정 zone p99 | ≥ 500ms | `zone_latency` |
| 30분 내 ERROR 로그 | ≥ 10건 | 보조 지표 (단독 사용 금지) |

복합 증상이면 심각도 높은 타입 우선: `error_spike` > `ccu_spike` > `queue_stuck` > `zone_latency`

## Step 3: 타입 확정 및 과거 사례 조회

이상 감지 결과로 인시던트 타입을 확정한 뒤 두 툴을 **동시에** 호출한다.

- `search_incidents_by_type(incident_type)` — 같은 타입 과거 인시던트 목록
- `get_resolution_steps(incident_type)` — 검증된 해결 방안 + 교훈

이상이 감지되지 않으면 "현재 지표 정상" 리포트를 출력하고 종료한다.

## Step 4: 의심 서비스 로그 집중 분석

타입에 따라 아래 서비스의 에러 로그를 추가 조회한다.

```
ccu_spike    → matchmaking, auth
queue_stuck  → matchmaking, redis
error_spike  → api-gateway, user-service, postgres
zone_latency → game-server
```

`search_logs(service=<서비스명>, level="ERROR", minutes=30)`

## Step 5: 진단 리포트 출력

아래 형식을 반드시 사용한다. 수집한 실제 수치와 과거 사례 데이터로 각 섹션을 채운다.

---

## 인시던트 진단 리포트

**진단 시각**: (UTC)  
**추정 타입**: `<incident_type>` | **심각도**: P1 / P2 / P3

### 현재 지표 스냅샷
| 지표 | 현재값 | 정상 범위 | 상태 |
|------|--------|----------|------|
| CCU | | | ✅ / ⚠️ / 🔴 |
| 에러율 | | < 1% | ✅ / ⚠️ / 🔴 |
| 매치메이킹 대기 | | < 60s | ✅ / ⚠️ / 🔴 |
| 최고 p99 레이턴시 | | < 200ms | ✅ / ⚠️ / 🔴 |

### 이상 감지 항목
(임계값 초과 항목과 수치, 해당 없으면 "없음")

### 근거 로그
(Step 4에서 발견된 대표 에러 메시지 1~3건)

### 즉각 대응 방안
(과거 사례 `resolution_steps` 기반, 우선순위 순으로 번호 목록)

1. ...
2. ...

### 모니터링 포인트
(해소 확인을 위해 계속 주시해야 할 지표와 목표값)

---

리포트 출력 후, 인시던트가 해소되면 `/postmortem`으로 사후 분석 문서를 작성할 것을 제안한다.
