---
name: incident-response
description: Game server incident diagnosis and response. Use this skill whenever the user reports or suspects a server problem — slow matchmaking, high error rates, lag spikes, CCU anomalies, queue backlogs, zone latency, or any "something feels wrong" signal. Also trigger when the user asks to check server health, investigate an alert, or diagnose unusual metrics. When in doubt, use this skill.
---

# 인시던트 대응 절차

게임 서버 장애를 진단하고 즉각 대응 방안을 도출하는 절차.
서브에이전트 3개를 순차 오케스트레이션해 메인 컨텍스트를 JSON 요약만으로 유지한다.

```
metrics-analyst → log-investigator → incident-classifier → 리포트 출력
```

## Step 1: metrics-analyst 호출

`metrics-analyst` 서브에이전트를 호출해 현재 메트릭 이상 여부를 파악한다.

반환된 JSON에서 다음 값을 추출한다.
- `primary_type`: 주요 인시던트 타입 (null이면 정상 → 리포트 출력 후 종료)
- `severity`: 심각도
- `anomalies`: 이상 항목 목록
- `snapshot`: 현재 지표값

## Step 2: log-investigator 호출

`primary_type` 에 따라 조사할 서비스를 결정하고 `log-investigator` 서브에이전트를 호출한다.

| primary_type | 조사 서비스 |
|-------------|-----------|
| `ccu_spike` | matchmaking |
| `queue_stuck` | matchmaking |
| `error_spike` | api-gateway |
| `zone_latency` | game-server |

호출 시 `service` 와 `incident_type` 을 프롬프트에 명시해 전달한다.

## Step 3: incident-classifier 호출

Step 1·2의 JSON 결과를 모두 `incident-classifier` 서브에이전트에 전달한다.
반환된 JSON에서 `confirmed_type`, `severity`, `resolution_steps`, `lessons_learned` 를 추출한다.

## Step 4: 진단 리포트 출력

아래 형식을 반드시 사용한다. 앞서 수집한 실제 수치로 각 섹션을 채운다.

---

## 인시던트 진단 리포트

**진단 시각**: (UTC)
**확정 타입**: `<confirmed_type>` | **심각도**: P1 / P2 / P3

### 현재 지표 스냅샷
| 지표 | 현재값 | 정상 범위 | 상태 |
|------|--------|----------|------|
| CCU | | < 5,000 | ✅ / ⚠️ / 🔴 |
| 에러율 | | < 1% | ✅ / ⚠️ / 🔴 |
| 매치메이킹 대기 | | < 60s | ✅ / ⚠️ / 🔴 |
| 최고 p99 레이턴시 | | < 200ms | ✅ / ⚠️ / 🔴 |

### 이상 감지 항목
(metrics-analyst anomalies 기반, 해당 없으면 "없음")

### 근거 로그
(log-investigator key_evidence 기반, 대표 에러 1~3건)

### 즉각 대응 방안
(incident-classifier resolution_steps 기반, 우선순위 순)

1. ...
2. ...

### 과거 사례 교훈
(incident-classifier lessons_learned)

### 모니터링 포인트
(해소 확인을 위해 계속 주시해야 할 지표와 목표값)

---

리포트 출력 후, 인시던트가 해소되면 `/postmortem`으로 사후 분석 문서를 작성할 것을 제안한다.
