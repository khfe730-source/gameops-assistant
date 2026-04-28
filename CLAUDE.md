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
- `mcp_servers/metrics_server.py`: CCU · 매치메이킹 큐 · 에러율 · 레이턴시

## Subagent 목록
(아직 없음 - Week 3부터 추가)

## Skills 목록
(아직 없음 - Week 2부터 추가)

## 협업 규칙 (Claude ↔ 사용자)

### Git / PR 워크플로
- 작업 완료 후 **직접 push 금지** — 반드시 PR로 올린다
- PR은 사용자가 검토·승인 후 **사용자가 직접 머지**한다
- PR을 올리기 전에 **테스트가 모두 통과**해야 한다
- 커밋은 리뷰가 쉽도록 **최대한 작은 단위**로 쪼갠다
  - 하나의 커밋 = 하나의 논리적 변경

### 코드 설계 원칙
- **단일 책임 원칙(SRP)** 준수 — 클래스·모듈은 변경 이유가 하나뿐이어야 한다
- 함수는 **최대한 작은 단위**로 쪼갠다 (한 함수 = 한 가지 일)
- 추상화는 필요한 시점에만 도입한다 (YAGNI)

### README.md 동기화 규칙
- 아래 변경이 생길 때마다 **README.md의 해당 섹션을 같은 PR·커밋에서 함께 수정**한다
  - 새 파일·모듈 추가 → `프로젝트 구조` 트리 업데이트
  - MCP 서버 추가/변경 → `구성 요소 > MCP 서버` 테이블 + `아키텍처` 다이어그램 업데이트
  - Subagent/Skill 추가 → 해당 테이블 상태 업데이트
  - 진행 상황 변경 → `진행 상황` 체크박스 업데이트
  - 사용법·테스트 방법 변경 → `사용 방법` / `테스트` 섹션 업데이트
- README.md는 항상 현재 코드와 일치해야 한다

### 작업 시 주의사항
- MCP 서버는 stdio로 통신하므로 stdout에 print 금지 (logging은 stderr로)
- 모킹 데이터는 결정적으로 생성 (시드 기반)
- 새 MCP 서버 추가 시 이 파일의 `MCP 서버 목록` 섹션 업데이트
