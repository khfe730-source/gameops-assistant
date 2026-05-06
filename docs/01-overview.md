# 01. 전체 아키텍처 개요

## 이 시스템은 무엇인가

게임 서버 운영자가 장애를 만났을 때 AI 어시스턴트에게 `/incident-response`를 입력하면,
여러 AI 에이전트가 협력해서 **메트릭 수집 → 로그 분석 → 과거 사례 조회 → 진단 리포트 생성**을
자동으로 수행하는 시스템이다.

---

## 구성 요소 한눈에 보기

```
┌─────────────────────────────────────────────────────────────┐
│  Claude Code (사용자 인터페이스)                              │
│                                                             │
│  /incident-response → Skill 실행                            │
│  /postmortem        → Skill 실행                            │
└──────────────────┬──────────────────────────────────────────┘
                   │ 오케스트레이션
                   ▼
┌─────────────────────────────────────────────────────────────┐
│  Subagents (.claude/agents/)                                │
│                                                             │
│  metrics-analyst  →  log-investigator  →  incident-classifier│
│  (메트릭 수집)        (로그 분석)           (타입 확정)         │
└──────────┬────────────────┬──────────────────┬──────────────┘
           │ MCP 툴 호출    │ MCP 툴 호출       │ MCP 툴 호출
           ▼                ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
│ metrics      │  │ log_search   │  │ incident_db          │
│ MCP 서버     │  │ MCP 서버     │  │ MCP 서버             │
│              │  │              │  │                      │
│ CCU          │  │ search_logs  │  │ list_recent          │
│ queue        │  │ error_logs   │  │ get_incident         │
│ error_rate   │  │ log_stats    │  │ search_by_type       │
│ latency      │  │ tail_logs    │  │ get_resolutions      │
└──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘
       │                 │                      │
       └─────────────────┴──────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  mock_data 패키지   │
              │                    │
              │  scenarios.py      │
              │  generators/       │
              │  fixtures/         │
              └─────────────────────┘
```

---

## 핵심 설계 결정 3가지

### 1. MCP(Model Context Protocol) 서버

MCP는 AI가 외부 툴을 호출하는 표준 프로토콜이다.
이 시스템에서는 **"메트릭 DB", "로그 시스템", "인시던트 DB"를 MCP 서버로 모킹**했다.

```
실제 시스템에서는:             이 시스템에서는:
Datadog API        →  metrics_server.py (mock)
Loki/Elastic       →  log_search_server.py (mock)
Confluence/JIRA    →  incident_db_server.py (mock)
```

**왜 MCP인가?** Claude Code가 `mcp__metrics__get_ccu_metrics`처럼 툴 이름으로 직접 호출할 수 있어서,
일반 Python 함수 호출과 달리 AI가 "어떤 데이터를 가져올지" 자율적으로 결정할 수 있다.

### 2. 서브에이전트 패턴

하나의 Claude 인스턴스가 모든 걸 처리하지 않고, **전문화된 서브에이전트 3개가 파이프라인을 형성**한다.

```
orchestrator (메인 Claude)
  ↓ 호출
  metrics-analyst   → JSON 반환  ← "메트릭만 본다"
  log-investigator  → JSON 반환  ← "로그만 본다"
  incident-classifier → JSON 반환 ← "종합 판단만 한다"
```

**왜 서브에이전트인가?** 각 에이전트가 전문화된 역할만 수행하므로
메인 컨텍스트 창을 JSON 요약만으로 유지할 수 있다.
모든 로그를 메인 컨텍스트에 쏟으면 토큰이 금방 고갈된다.

### 3. 시나리오 기반 모킹

실제 서버가 없어도 **환경변수 하나로 어떤 장애 상황이든 재현**할 수 있다.

```bash
# .mcp.json에서 시나리오 전환
"env": {"METRICS_SCENARIO": "incident_error_spike"}
```

가능한 시나리오:

| 시나리오 | 설명 |
|---------|------|
| `normal` | 모든 지표 정상 |
| `incident_ccu_spike` | 동접자 3배 급증 |
| `incident_queue_stuck` | 매치메이킹 큐 완전 정체 |
| `incident_error_spike` | 에러율 15-30% 폭등 |
| `incident_zone_latency` | 특정 존 레이턴시 급등 |

---

## 데이터 흐름 (end-to-end)

사용자가 `/incident-response`를 입력했을 때 실제로 일어나는 일:

```
1. 스킬 파일 로드
   └─ .claude/skills/incident-response/SKILL.md 읽힘

2. Step 1: metrics-analyst 서브에이전트 실행
   └─ 서브에이전트 프롬프트 + .claude/agents/metrics-analyst.md 로드
   └─ 4개 MCP 툴 병렬 호출:
      mcp__metrics__get_ccu_metrics()
      mcp__metrics__get_error_rate_metrics()
      mcp__metrics__get_latency_metrics()
      mcp__metrics__get_matchmaking_queue_metrics()
   └─ metrics_server.py 실행 → mock_data.scenarios → generators → 수치 반환
   └─ 이상 감지 로직 → JSON 반환

3. Step 2: log-investigator 서브에이전트 실행
   └─ primary_type 기반으로 서비스 결정
   └─ MCP 툴 호출:
      mcp__log_search__get_error_logs(service="api-gateway")
      mcp__log_search__get_log_stats()
   └─ log_search_server.py → generators/logs → 로그 엔트리 반환
   └─ 패턴 분석 → JSON 반환

4. Step 3: incident-classifier 서브에이전트 실행
   └─ metrics JSON + log JSON 수신
   └─ MCP 툴 호출:
      mcp__incident_db__search_incidents_by_type()
      mcp__incident_db__get_resolution_steps()
   └─ incident_db_server.py → generators/incident_db → 정적 레코드 반환
   └─ 타입 확정 + 해결 방안 → JSON 반환

5. Step 4: 진단 리포트 출력
   └─ 1~3단계 JSON을 마크다운 표로 렌더링
```

---

## 디렉토리 구조와 역할

```
gameops-assistant/
├── .claude/
│   ├── agents/          ← 서브에이전트 정의 (프롬프트 + 역할)
│   ├── skills/          ← 스킬 정의 (오케스트레이션 절차)
│   └── settings.local.json ← MCP 툴 자동 허용 목록
│
├── .mcp.json            ← MCP 서버 3개 등록 + 시나리오 설정
│
├── mcp_servers/         ← MCP 서버 구현체
│   ├── metrics_server.py
│   ├── incident_db_server.py
│   └── log_search_server.py
│
├── mock_data/           ← 가짜 데이터 생성 엔진
│   ├── scenarios.py     ← 파사드 (진입점)
│   ├── generators/      ← 도메인별 생성기
│   └── fixtures/        ← 골든 스냅샷 (회귀 테스트용)
│
├── tests/               ← pytest 테스트 (121 케이스)
│
└── postmortems/         ← 포스트모템 문서 저장소
```

---

## 다음으로 읽을 문서

- MCP 서버가 어떻게 동작하는지 → [02-mcp-servers.md](02-mcp-servers.md)
- 모킹 데이터가 어떻게 만들어지는지 → [03-mock-data.md](03-mock-data.md)
