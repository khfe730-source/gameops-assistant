---
name: postmortem
description: Game server incident postmortem (사후 분석) document creation. Use after an incident has been resolved — when the user wants to document what happened, the root cause, impact, and action items. Trigger when user says /postmortem or asks to write a postmortem / 포스트모템.
---

# 포스트모템 작성 절차

인시던트 종료 후 사후 분석 문서를 작성하는 절차.
`/incident-response` 진단 리포트 결과를 이어받아 실행하는 것이 이상적이다.

## Step 1: 인시던트 컨텍스트 확인

대화 맥락에서 아래 정보를 추출한다.
없는 항목만 사용자에게 질문한다 (있는 정보는 다시 묻지 않는다).

| 항목 | 출처 |
|------|------|
| 인시던트 타입 | `/incident-response` 결과 또는 사용자 입력 |
| 발생 시각 (UTC) | `/incident-response` 진단 시각 또는 사용자 입력 |
| 인시던트 중 최고 지표값 | `/incident-response` 스냅샷 또는 사용자 입력 |
| 해소 시각 (UTC) | 사용자 입력 |
| 적용한 해결 조치 | `/incident-response` 즉각 대응 방안 또는 사용자 입력 |

## Step 2: 과거 사례 및 해결책 조회

두 툴을 **동시에** 호출한다.

- `search_incidents_by_type(incident_type)` — 같은 타입 과거 인시던트 목록
- `get_resolution_steps(incident_type)` — 검증된 해결 방안 + lessons_learned

## Step 3: 현재 지표 재확인 (해소 검증)

4개 메트릭 툴을 **동시에** 호출해 지표가 정상으로 돌아왔는지 확인한다.

- `get_ccu_metrics`
- `get_error_rate_metrics`
- `get_latency_metrics`
- `get_matchmaking_queue_metrics`

## Step 4: 포스트모템 문서 출력

아래 형식을 반드시 사용한다. 수집한 실제 수치와 과거 사례 데이터로 각 섹션을 채운다.

---

## 포스트모템 — `<incident_type>`

**작성 시각**: (UTC)
**심각도**: P1 / P2 / P3

---

### 1. 요약 (Executive Summary)

(무슨 일이 있었는지, 영향 범위, 해소 여부를 2문장 이내로 기술)

### 2. 타임라인

| 시각 (UTC) | 이벤트 |
|-----------|--------|
| HH:MM | 인시던트 최초 감지 (`/incident-response` 실행 시각) |
| HH:MM | 원인 특정 |
| HH:MM | 대응 조치 시작 |
| HH:MM | 지표 정상 복귀 확인 |

타임라인 항목은 알 수 없는 시각은 "미확인"으로 표기하고 칸을 비우지 않는다.

### 3. 영향 범위

| 지표 | 인시던트 중 최고값 | 정상 범위 | 상태 |
|------|-----------------|----------|------|
| CCU | | < 5,000 | 🔴 |
| 에러율 | | < 1% | 🔴 |
| 매치메이킹 대기 | | < 60s | 🔴 |
| p99 레이턴시 (최악 zone) | | < 200ms | 🔴 |

- 영향 받은 서비스: (Step 2 과거 사례 기반으로 나열)
- 추정 영향 유저 수: (인시던트 당시 CCU 기반 추정)

### 4. 근본 원인 (Root Cause)

(과거 사례 `resolution_steps` 및 `lessons_learned`를 바탕으로 이번 인시던트의 근본 원인 서술.
단순 증상 설명이 아니라 "왜 그런 증상이 발생했는가"를 기술한다.)

### 5. 해결 과정

(Step 2 `resolution_steps` 중 이번에 실제로 적용한 조치를 순서대로 기술)

1. ...
2. ...

### 6. 재발 방지 액션 아이템

(과거 사례 `lessons_learned` 기반으로 구체적이고 실행 가능한 액션을 도출한다.
담당자와 기한은 "TBD"로 표기해도 된다.)

| # | 액션 | 담당 | 기한 |
|---|------|------|------|
| 1 | | TBD | TBD |
| 2 | | TBD | TBD |

### 7. 현재 지표 (해소 확인)

Step 3 재조회 결과로 채운다.

| 지표 | 현재값 | 정상 범위 | 상태 |
|------|--------|----------|------|
| CCU | | < 5,000 | ✅ / ⚠️ / 🔴 |
| 에러율 | | < 1% | ✅ / ⚠️ / 🔴 |
| 매치메이킹 대기 | | < 60s | ✅ / ⚠️ / 🔴 |
| p99 레이턴시 | | < 200ms | ✅ / ⚠️ / 🔴 |

지표 중 하나라도 🔴 이면 "**주의: 인시던트가 아직 완전히 해소되지 않았을 수 있습니다.**"를 문서 최상단에 추가한다.

---

문서 출력 후, 아래 두 가지를 제안한다.

1. **파일 저장**: `postmortems/YYYY-MM-DD_<incident_type>.md` 경로에 저장할지 묻는다.
2. **후속 일정**: 재발 방지 액션 아이템의 진행 상황을 추적할 스케줄 에이전트(`/schedule`)를 제안한다.
