"""Static past-incident records with query helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

IncidentType = Literal["ccu_spike", "queue_stuck", "error_spike", "zone_latency"]

_RECORDS: list[dict] = [
    {
        "incident_id": "INC-2026-001",
        "type": "ccu_spike",
        "severity": "P1",
        "title": "CCU 3× 폭증 — 글로벌 패치 직후 동접 폭발",
        "started_at": "2026-03-15T14:00:00Z",
        "resolved_at": "2026-03-15T15:45:00Z",
        "duration_minutes": 105,
        "affected_components": ["matchmaking", "game-session", "auth"],
        "summary": (
            "v2.3.0 패치 배포 직후 전체 CCU가 평소의 3배로 폭증. "
            "매치메이킹 큐 과부하로 평균 대기시간 8분 초과, 에러율 10% 상승."
        ),
        "root_cause": (
            "패치 노트 공개 후 대규모 유저 유입. "
            "오토스케일 정책이 scale-out 트리거 임계값(CCU +50%)보다 늦게 반응(지연 7분)."
        ),
        "resolution_steps": [
            "매치메이킹 서버 수동 스케일아웃 (2× → 6× 인스턴스)",
            "큐 컨커런시 한도 일시 상향 (500 → 2000)",
            "오토스케일 트리거 임계값 하향 조정 (50% → 20%)",
            "게임 로비 대기열 안내 팝업 활성화",
        ],
        "lessons_learned": (
            "오토스케일 cool-down 기간(5분)이 급격한 CCU 급등에 대응하지 못함. "
            "패치 배포 전 예비 인스턴스 사전 프로비저닝 필요."
        ),
    },
    {
        "incident_id": "INC-2026-002",
        "type": "queue_stuck",
        "severity": "P2",
        "title": "매치메이킹 큐 데드락 — Redis 연결 풀 고갈",
        "started_at": "2026-03-22T09:15:00Z",
        "resolved_at": "2026-03-22T10:30:00Z",
        "duration_minutes": 75,
        "affected_components": ["matchmaking", "redis"],
        "summary": (
            "매치메이킹 큐 평균 대기 시간이 20분 이상으로 고착. "
            "신규 매칭 생성 불가 상태 지속."
        ),
        "root_cause": (
            "Redis 연결 풀 크기(100) 초과. "
            "매치메이킹 워커가 연결을 반납하지 않아 풀 고갈 → 큐 처리 중단."
        ),
        "resolution_steps": [
            "매치메이킹 서비스 재시작으로 Redis 연결 강제 해제",
            "Redis maxmemory-policy 확인 및 eviction 정책 점검",
            "연결 풀 크기 100 → 300으로 상향",
            "연결 누수 방지를 위해 context manager 패턴 적용 (핫픽스)",
        ],
        "lessons_learned": (
            "Redis 연결 반납 누락은 높은 트래픽에서만 표면화됨. "
            "연결 풀 사용률 알람(80% 이상) 추가 필요."
        ),
    },
    {
        "incident_id": "INC-2026-003",
        "type": "error_spike",
        "severity": "P1",
        "title": "에러율 25% 급증 — DB 커넥션 타임아웃",
        "started_at": "2026-04-01T03:30:00Z",
        "resolved_at": "2026-04-01T04:15:00Z",
        "duration_minutes": 45,
        "affected_components": ["api-gateway", "user-service", "postgres"],
        "summary": (
            "새벽 유지보수 중 PostgreSQL 슬로우 쿼리 증가로 에러율이 25%까지 급등. "
            "결제·로그인 API 응답 불가."
        ),
        "root_cause": (
            "인덱스 REINDEX 작업이 테이블 락을 점유. "
            "동시 요청이 커넥션 풀 대기 → 타임아웃(30초) 초과."
        ),
        "resolution_steps": [
            "REINDEX 작업 즉시 중단 (pg_cancel_backend)",
            "장기 락 보유 세션 강제 종료",
            "커넥션 풀 타임아웃 30s → 5s로 단축해 빠른 실패 전환",
            "에러율 정상화(< 1%) 확인 후 REINDEX CONCURRENTLY로 재실행",
        ],
        "lessons_learned": (
            "REINDEX는 CONCURRENTLY 옵션 없이 실행하면 락을 점유. "
            "유지보수 작업은 사전 영향도 검토 체크리스트 필수화."
        ),
    },
    {
        "incident_id": "INC-2026-004",
        "type": "zone_latency",
        "severity": "P2",
        "title": "ap-northeast-1 레이턴시 급등 — AWS 리전 네트워크 이슈",
        "started_at": "2026-04-10T18:00:00Z",
        "resolved_at": "2026-04-10T19:20:00Z",
        "duration_minutes": 80,
        "affected_components": ["game-server", "ap-northeast-1"],
        "summary": (
            "ap-northeast-1 리전 p99 레이턴시 5000ms 초과. "
            "해당 리전 유저 게임플레이 불가 수준 지연."
        ),
        "root_cause": (
            "AWS ap-northeast-1 리전 내 네트워크 혼잡 (AWS 공식 공지 확인). "
            "외부 원인으로 서버 측 조치 한계."
        ),
        "resolution_steps": [
            "AWS Health Dashboard 확인 → 리전 이슈 공지 확인",
            "ap-northeast-1 유저 트래픽을 ap-northeast-2로 임시 라우팅",
            "게임 클라이언트에 '서버 이전 중' 공지 표시",
            "AWS 이슈 해소 후 원래 리전으로 순차 복구",
        ],
        "lessons_learned": (
            "단일 리전 의존도가 높은 상태. "
            "리전 장애 시 자동 트래픽 페일오버 메커니즘 구축 필요."
        ),
    },
    {
        "incident_id": "INC-2025-021",
        "type": "ccu_spike",
        "severity": "P2",
        "title": "CCU 2× 폭증 — 인플루언서 방송 이벤트",
        "started_at": "2025-11-20T20:00:00Z",
        "resolved_at": "2025-11-20T21:30:00Z",
        "duration_minutes": 90,
        "affected_components": ["matchmaking", "auth"],
        "summary": (
            "대형 스트리머 방송 시작과 동시에 CCU 2배 폭증. "
            "로그인 서버 지연 및 매치 대기 시간 5분 초과."
        ),
        "root_cause": (
            "예측하지 못한 외부 이벤트(방송)로 인한 급격한 유입. "
            "오토스케일이 3분 후 반응했으나 그 사이 큐 적체."
        ),
        "resolution_steps": [
            "로그인 서버 수동 스케일아웃 (2× → 4×)",
            "매치메이킹 큐 컨커런시 한도 상향",
            "이후 30분 내 CCU 자연 안정화",
        ],
        "lessons_learned": (
            "마케팅·파트너 팀과 대형 외부 이벤트 사전 공유 채널 필요. "
            "예고 없는 트래픽 급등 대비 예비 인스턴스 상시 대기 정책 검토."
        ),
    },
    {
        "incident_id": "INC-2025-015",
        "type": "error_spike",
        "severity": "P2",
        "title": "에러율 18% — 잘못된 배포로 인한 NPE",
        "started_at": "2025-09-05T11:00:00Z",
        "resolved_at": "2025-09-05T11:40:00Z",
        "duration_minutes": 40,
        "affected_components": ["user-service", "inventory-service"],
        "summary": (
            "v2.1.5 핫픽스 배포 직후 NullPointerException 다발. "
            "아이템 인벤토리 조회 API 에러율 18% 기록."
        ),
        "root_cause": (
            "핫픽스 코드에서 옵셔널 필드 null 체크 누락. "
            "스테이징 환경에는 해당 데이터 없어 QA 통과."
        ),
        "resolution_steps": [
            "v2.1.5 즉시 롤백 → v2.1.4로 복구",
            "에러율 정상화(< 1%) 확인",
            "null 체크 추가 후 v2.1.6으로 재배포",
        ],
        "lessons_learned": (
            "스테이징 데이터가 프로덕션 엣지 케이스를 커버하지 못함. "
            "카나리 배포 도입 및 스테이징 데이터 다양성 보강 필요."
        ),
    },
    {
        "incident_id": "INC-2025-008",
        "type": "queue_stuck",
        "severity": "P3",
        "title": "매치메이킹 큐 고착 — 랭크 구간 불균형",
        "started_at": "2025-07-12T15:00:00Z",
        "resolved_at": "2025-07-12T16:10:00Z",
        "duration_minutes": 70,
        "affected_components": ["matchmaking"],
        "summary": (
            "특정 랭크 구간(다이아몬드 5~플래티넘 1) 매칭 대기 25분 이상. "
            "전체 큐는 정상이나 해당 구간만 고착."
        ),
        "root_cause": (
            "랭크 개편 후 인구가 얇은 구간이 생성됨. "
            "매칭 알고리즘이 엄격한 MMR 범위를 유지해 매칭 불가 상태 지속."
        ),
        "resolution_steps": [
            "해당 구간 MMR 허용 범위 임시 확대 (±50 → ±150)",
            "대기 중인 유저에게 인게임 공지 발송",
            "장기적으로 인구 분포 기반 동적 MMR 범위 조정 기능 기획",
        ],
        "lessons_learned": (
            "랭크 구간 개편 시 인구 분포 시뮬레이션 필수. "
            "큐 고착 탐지 알람 추가 (특정 구간 대기 10분 이상)."
        ),
    },
    {
        "incident_id": "INC-2025-003",
        "type": "zone_latency",
        "severity": "P1",
        "title": "us-west-2 레이턴시 급등 — DDoS 공격",
        "started_at": "2025-05-30T22:00:00Z",
        "resolved_at": "2025-05-30T23:30:00Z",
        "duration_minutes": 90,
        "affected_components": ["game-server", "us-west-2", "ddos-protection"],
        "summary": (
            "us-west-2 리전 p99 레이턴시 8000ms 초과. DDoS 공격으로 확인. "
            "북미 유저 전체 게임플레이 불가."
        ),
        "root_cause": (
            "외부 DDoS 공격 (UDP flood). "
            "AWS Shield Standard로는 트래픽 흡수 한계 초과."
        ),
        "resolution_steps": [
            "AWS Shield Advanced 일시 활성화",
            "의심 IP 대역 WAF 블랙리스트 적용",
            "트래픽을 us-east-1로 임시 우회",
            "CloudFront 앞단 배치로 오리진 IP 은닉",
        ],
        "lessons_learned": (
            "AWS Shield Advanced 상시 활성화 검토 (비용 대비 안정성 우선). "
            "DDoS 공격 탐지 → 자동 방어 스크립트 구축."
        ),
    },
]


def list_recent(hours: int = 24) -> list[dict]:
    """Return incidents started within the last `hours` hours, newest first."""
    now = datetime.now(tz=timezone.utc)
    cutoff_ts = now.timestamp() - hours * 3600
    result = [
        inc for inc in _RECORDS
        if datetime.fromisoformat(inc["started_at"].replace("Z", "+00:00")).timestamp() >= cutoff_ts
    ]
    return sorted(result, key=lambda x: x["started_at"], reverse=True)


def get_by_id(incident_id: str) -> dict | None:
    """Return the incident matching `incident_id`, or None if not found."""
    for inc in _RECORDS:
        if inc["incident_id"] == incident_id:
            return inc
    return None


def search_by_type(incident_type: IncidentType) -> list[dict]:
    """Return all incidents of the given type, newest first."""
    result = [inc for inc in _RECORDS if inc["type"] == incident_type]
    return sorted(result, key=lambda x: x["started_at"], reverse=True)


def get_resolutions(incident_type: IncidentType) -> list[dict]:
    """Return resolution info from past incidents of `incident_type`, newest first."""
    return [
        {
            "incident_id": inc["incident_id"],
            "severity": inc["severity"],
            "title": inc["title"],
            "root_cause": inc["root_cause"],
            "resolution_steps": inc["resolution_steps"],
            "lessons_learned": inc["lessons_learned"],
        }
        for inc in search_by_type(incident_type)
    ]
