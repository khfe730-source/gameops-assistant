# Game Server Operations Assistant

## 프로젝트 목적
게임 서버 운영자를 위한 AI 어시스턴트.
실시간 메트릭·로그·과거 인시던트를 종합해 장애 진단을 돕고,
포스트모템 작성까지 자동화하는 시스템.

이 프로젝트는 학습 목적이며, MCP 서버 / Skills / Subagent 패턴을
실전 시나리오로 익히는 것이 목표.

## 기술 스택
- 언어: Python 3.12
- 패키지 매니저: uv
- MCP SDK: `mcp` (공식 Python SDK)
- 클라이언트: Claude Code (stdio transport)

## 디렉토리 구조
- `mcp_servers/`: MCP 서버 구현 (각 서버는 독립 프로세스)
- `mock_data/`: 가짜 게임 데이터 생성기 + 미리 정의된 시나리오
- `.claude/agents/`: Custom Subagent 정의 (markdown)
- `.claude/skills/`: Skills (절차적 지식)
- `tests/`: 단위/통합 테스트

## 코딩 컨벤션
- 타입 힌트 필수 (Pydantic 활용)
- Docstring은 함수 시그니처 위에 한 줄 요약 + 인자 설명
- 린터: ruff (기본 설정)
- 테스트: pytest, 함수당 최소 1개 happy path

## MCP 서버 목록
(아직 없음 - Day 2부터 추가)

## Subagent 목록
(아직 없음 - Week 3부터 추가)

## Skills 목록
(아직 없음 - Week 2부터 추가)

## 작업 시 주의사항
- MCP 서버는 stdio로 통신하므로 stdout에 print 금지 (logging은 stderr로)
- 모킹 데이터는 결정적으로 생성 (시드 기반)
- 새 MCP 서버 추가 시 이 파일의 `MCP 서버 목록` 섹션 업데이트
