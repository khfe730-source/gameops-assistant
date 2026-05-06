# 학습 문서 인덱스

이 디렉토리는 `gameops-assistant` 시스템을 처음부터 이해하기 위한 학습 문서 모음입니다.
AI가 개발한 코드를 분석·정리한 내용입니다.

## 순서대로 읽기

| 문서 | 내용 | 읽는 이유 |
|------|------|----------|
| [01-overview.md](01-overview.md) | 전체 아키텍처, 핵심 개념, 데이터 흐름 | 시스템이 왜 이런 구조인지 파악 |
| [02-mcp-servers.md](02-mcp-servers.md) | MCP 서버 3개 상세 분석 | 실제 데이터가 어디서 오는지 이해 |
| [03-mock-data.md](03-mock-data.md) | 시나리오·생성기·픽스처 구조 | 모킹 데이터가 어떻게 만들어지는지 이해 |
| [04-agents-skills.md](04-agents-skills.md) | 서브에이전트 + 스킬 오케스트레이션 | AI 멀티에이전트 패턴 이해 |
| [05-testing.md](05-testing.md) | 테스트 전략과 121개 케이스 구조 | 시스템을 검증하는 방법 이해 |

## 핵심 개념 요약

```
사용자 → /incident-response 스킬
           │
           ├─ metrics-analyst (서브에이전트)
           │    └─ MCP: metrics 서버 4개 툴 동시 호출
           │
           ├─ log-investigator (서브에이전트)
           │    └─ MCP: log_search 서버 2개 툴 동시 호출
           │
           ├─ incident-classifier (서브에이전트)
           │    └─ MCP: incident_db 서버 2개 툴 동시 호출
           │
           └─ 진단 리포트 출력
```

## 빠른 참조

- 시나리오 목록: `normal`, `incident_ccu_spike`, `incident_queue_stuck`, `incident_error_spike`, `incident_zone_latency`
- MCP 서버: `metrics_server.py`, `incident_db_server.py`, `log_search_server.py`
- 서브에이전트: `.claude/agents/` (4개)
- 스킬: `.claude/skills/` (2개)
- 테스트: `tests/` (121 케이스)
