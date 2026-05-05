---
name: postmortem
description: Game server incident postmortem (사후 분석) document creation. Use after an incident has been resolved — when the user wants to document what happened, the root cause, impact, and action items. Trigger when user says /postmortem or asks to write a postmortem / 포스트모템.
---

# 포스트모템 작성 절차

인시던트 종료 후 사후 분석 문서를 작성하는 절차.
`/incident-response` 진단 리포트 결과를 이어받아 실행하는 것이 이상적이다.

```
postmortem-writer (subagent) → 문서 출력
```

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

## Step 2: postmortem-writer 서브에이전트 호출

`postmortem-writer` 서브에이전트를 호출해 과거 사례 조회와 현재 지표 재확인을 위임한다.

프롬프트에 아래 세 값을 명시해 전달한다.

- `incident_type`: Step 1에서 확정한 인시던트 타입
- `peak_metrics`: Step 1에서 수집한 인시던트 중 최고 지표값 (없으면 null)
- `applied_steps`: Step 1에서 수집한 적용 조치 목록 (없으면 빈 배열)

반환된 JSON에서 다음 값을 추출한다.

- `current_metrics`: 현재 지표 스냅샷 + `all_normal` 플래그
- `past_incidents`: 과거 동일 타입 인시던트 목록
- `resolution_steps`: 검증된 해결 방안
- `lessons_learned`: 가장 최근 사례 교훈
- `affected_services`: 영향 서비스 목록

## Step 3: 포스트모템 문서 출력

`current_metrics.all_normal` 이 `false` 이면 문서 최상단에 아래 경고를 추가한다.

> **주의: 인시던트가 아직 완전히 해소되지 않았을 수 있습니다.**

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

- 영향 받은 서비스: (`past_incidents` + `affected_services` 기반으로 나열)
- 추정 영향 유저 수: (인시던트 당시 CCU 기반 추정)

### 4. 근본 원인 (Root Cause)

(`past_incidents` 및 `lessons_learned`를 바탕으로 이번 인시던트의 근본 원인 서술.
단순 증상 설명이 아니라 "왜 그런 증상이 발생했는가"를 기술한다.)

### 5. 해결 과정

(`resolution_steps` 중 이번에 실제로 적용한 조치를 순서대로 기술)

1. ...
2. ...

### 6. 재발 방지 액션 아이템

(`lessons_learned` 기반으로 구체적이고 실행 가능한 액션을 도출한다.
담당자와 기한은 "TBD"로 표기해도 된다.)

| # | 액션 | 담당 | 기한 |
|---|------|------|------|
| 1 | | TBD | TBD |
| 2 | | TBD | TBD |

### 7. 현재 지표 (해소 확인)

`current_metrics` 재조회 결과로 채운다.

| 지표 | 현재값 | 정상 범위 | 상태 |
|------|--------|----------|------|
| CCU | | < 5,000 | ✅ / ⚠️ / 🔴 |
| 에러율 | | < 1% | ✅ / ⚠️ / 🔴 |
| 매치메이킹 대기 | | < 60s | ✅ / ⚠️ / 🔴 |
| p99 레이턴시 | | < 200ms | ✅ / ⚠️ / 🔴 |

---

문서 출력 후, 아래 두 가지를 제안한다.

1. **파일 저장**: `postmortems/YYYY-MM-DD_<incident_type>.md` 경로에 저장할지 묻는다.
2. **후속 일정**: 재발 방지 액션 아이템의 진행 상황을 추적할 스케줄 에이전트(`/schedule`)를 제안한다.
