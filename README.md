# Game Server Operations Assistant

게임 서버 운영을 위한 LLM 기반 어시스턴트.
MCP 서버 / Custom Skills / Subagent를 활용한 4주 학습 프로젝트.

## 학습 목표
- MCP (Model Context Protocol) 서버 직접 구현
- Claude Code의 Skills로 절차적 지식 주입
- Subagent로 컨텍스트 분리 및 병렬 처리
- 게임 서버 운영 도메인을 LLM 워크플로로 자동화

---

## 프로젝트 구조

```
gameops-assistant/
├── mcp_servers/                # MCP 서버 (각 서버는 독립 프로세스)
│   ├── __init__.py
│   ├── metrics_server.py       # CCU · 큐 · 에러율 · 레이턴시 (구현 완료)
│   ├── incident_db_server.py   # 과거 장애 이력 조회 (구현 완료)
│   └── log_search_server.py    # 로그 검색 Loki/Elastic 모킹 (구현 완료)
│
├── mock_data/                  # 결정적 가짜 데이터 생성기
│   ├── __init__.py
│   ├── scenarios.py            # 시나리오별 메트릭 파사드 (구현 완료)
│   ├── generators/
│   │   ├── metrics/
│   │   │   ├── normal.py              # 정상 상태 메트릭 생성기 (구현 완료)
│   │   │   └── incident.py            # 인시던트 상태 메트릭 생성기 (구현 완료)
│   │   ├── incident_db/
│   │   │   └── records.py             # 과거 인시던트 정적 레코드 + 쿼리 함수 (구현 완료)
│   │   └── logs/
│   │       └── entries.py             # 시나리오별 로그 엔트리 생성기 + 쿼리 함수 (구현 완료)
│   └── fixtures/               # 시나리오별 정적 스냅샷 JSON (구현 완료)
│
├── .claude/
│   ├── agents/                 # Custom Subagent 정의 (markdown)
│   └── skills/
│       ├── incident-response/  # 단계별 인시던트 진단·대응 (구현 완료)
│       └── postmortem/         # 인시던트 사후 분석 문서 작성 (구현 완료)
│
├── tests/
│   ├── test_metrics_generator.py
│   └── test_scenarios.py
│
├── main.py
├── pyproject.toml
└── CLAUDE.md
```

---

## 시작하기

### 요구사항
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) 패키지 매니저
- [Claude Code](https://claude.ai/code) CLI

### 설치

```bash
# 저장소 클론
git clone https://github.com/khfe730-source/gameops-assistant.git
cd gameops-assistant

# 의존성 설치
uv sync
```

---

## 사용 방법

### 1. MCP 서버를 Claude Code에 등록

프로젝트 루트에 `.mcp.json` 파일을 생성합니다.

`.mcp.json` (프로젝트 루트에 포함되어 있으므로 별도 설정 불필요)

```json
{
  "mcpServers": {
    "metrics": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_servers.metrics_server"]
    }
  }
}
```

인시던트 시나리오를 시뮬레이션하려면 환경변수로 시나리오를 선택합니다.

```json
{
  "mcpServers": {
    "metrics": {
      "command": "uv",
      "args": ["run", "python", "-m", "mcp_servers.metrics_server"],
      "env": {
        "METRICS_SCENARIO": "incident_ccu_spike"
      }
    }
  }
}
```

지원 시나리오:
| 시나리오 | 설명 |
|---------|------|
| `normal` (기본값) | 정상 상태 |
| `incident_ccu_spike` | CCU 3배 폭증 · 큐 과부하 · 에러율 상승 |
| `incident_queue_stuck` | 매치메이킹 큐 고착 (15–30분 대기) |
| `incident_error_spike` | 에러율 급증 (15–30%) |
| `incident_zone_latency` | ap-northeast-1 레이턴시 급증 (p99 > 5000ms) |

### 2. Claude Code에서 메트릭 조회

MCP 서버 등록 후 Claude Code에서 자연어로 질의합니다.

```
지금 CCU 얼마야?
매치메이킹 큐 상태 알려줘
서버 레이턴시 확인해줘
```

### 3. 핵심 시나리오 (전체 완성 후)

> "지금 매치메이킹 큐가 평소보다 길어. 원인 파악하고 대응 방안 알려줘"

1. 메인 에이전트가 **메트릭 서브에이전트** + **로그 서브에이전트** 병렬 호출
2. 양쪽 결과를 종합해 병목 원인 특정
3. **인시던트 대응 Skill** 참조 → 단계별 완화·복구 가이드 출력
4. 인시던트 종료 후 **포스트모템 서브에이전트**가 문서 자동 생성

---

## 테스트

```bash
# 전체 테스트 실행
uv run pytest

# 특정 파일만
uv run pytest tests/test_metrics_generator.py -v

# 린터
uv run ruff check .
```

현재 테스트 커버리지:

| 모듈 | 테스트 파일 | 케이스 수 |
|------|------------|----------|
| `mock_data/generators/metrics/normal.py` | `tests/test_metrics_generator.py` | 14 |
| `mock_data/scenarios.py` + `generators/metrics/incident.py` | `tests/test_scenarios.py` | 22 |
| `mock_data/generators/incident_db/records.py` | `tests/test_incident_db.py` | 18 |
| `mock_data/generators/logs/entries.py` | `tests/test_log_search.py` | 35 |

---

## 아키텍처

```
사용자 질의
    │
    ▼
메인 에이전트 (Claude)
    ├─ [MCP] 메트릭 서버  ─── CCU, 매치메이킹 큐, 에러율, 레이턴시  ✅
    ├─ [MCP] 인시던트 DB  ─── 과거 장애 이력 · 해결 방법  ✅
    └─ [MCP] 로그 검색    ─── Loki/Elastic 모킹  ✅
    │
    ├─ [Subagent] 메트릭 분석 전문가  ┐ 병렬 실행
    └─ [Subagent] 로그 분석 전문가    ┘
    │
    ├─ [Skill] 인시던트 대응 절차  ─── 단계별 진단·완화·복구
    └─ [Skill] 포스트모템 작성 가이드
    │
    ▼
[Subagent] 포스트모템 작성자  ─── 결과 정리 · 문서 자동 생성
```

---

## 구성 요소

### MCP 서버
| 서버 | 역할 | 상태 |
|------|------|------|
| `metrics_server` | CCU · 매치메이킹 큐 · 에러율 · 레이턴시 제공 | ✅ 완료 |
| `incident_db_server` | 과거 장애 이력 · 해결 방법 조회 | ✅ 완료 |
| `log_search_server` | Loki/Elastic 모킹, 로그 검색 | ✅ 완료 |

### Subagent
| 에이전트 | 역할 | 상태 |
|----------|------|------|
| `metrics_analyst` | 이상 패턴 탐지 · 메트릭 해석 | ✅ 완료 |
| `log_investigator` | 에러 원인 추적 · 로그 파싱 | ✅ 완료 |
| `postmortem_writer` | 인시던트 결과 정리 · 문서 생성 | 미구현 |

### Skills
| 스킬 | 역할 | 상태 |
|------|------|------|
| `incident-response` | 메트릭·로그·과거사례 기반 단계별 진단·대응 | ✅ 완료 |
| `postmortem` | 타임라인·근본원인·재발방지 액션 아이템 포함 사후 분석 문서 작성 | ✅ 완료 |

---

## 진행 상황
- [x] 환경 셋업
- [x] MCP 서버 1 — 메트릭 서버 + 모킹 데이터 생성기
- [x] 모킹 시나리오 (정상 vs 인시던트 상태)
- [x] MCP 서버 2 — 인시던트 DB 서버
- [x] MCP 서버 3 — 로그 검색 서버
- [x] Skill 1 — 인시던트 대응 (`incident-response`)
- [x] Skill 2 — 포스트모템 (`postmortem`)
- [x] Subagent 1 — 메트릭 분석 (`metrics_analyst`)
- [x] Subagent 2 — 로그 분석 (`log_investigator`)
- [ ] Subagent 3 — 포스트모템 작성 (`postmortem_writer`)
- [ ] 전체 시나리오 통합 테스트 · 문서화

## 라이선스
MIT
