"""
LangGraph 에이전트 상태 정의.
노드 간에 공유되는 단일 상태 객체(TypedDict)로, 각 노드가 이 상태를 참조하거나 업데이트한다.
"""

from typing import TypedDict, Optional, Any, List, Dict, Literal


class AgentState(TypedDict, total=False):
    """
    에이전트의 전체 워크플로우 상태.
    라우팅, 도구 실행, 결과 검증, 재시도, 응답 생성에 이르는 전 과정의 데이터가 저장된다.
    """

    # ── [1. 입력 정보] chat_service에서 대화 시작 시 초기화 ──
    
    user_message: str
    # 사용자가 입력한 원본 텍스트 메시지 (라우팅, 파라미터 추출, 최종 응답에 참고)
    
    student_name: Optional[str]
    # 로그인된 수강생 이름 (개인화된 문구 생성에 활용, 미로그인 시 None)
    
    chat_history: List[Dict[str, str]]
    # 이전 대화 내역 목록 (맥락 파악 및 연속 대화를 위한 히스토리 백업)
    
    trace_id: Optional[str]
    # Langfuse 모니터링 추적용 ID (동일 턴의 모든 관측치를 단일 트레이스로 연계)
    
    _db: Any
    # SQLAlchemy 비동기 DB 세션 (서브에이전트 내부의 ToolExecutor가 DB 접근 시 사용)

    # ── [2. 라우터 정보] router_node에 의해 판정 및 기록 ──
    
    intent: str
    # 사용자 입력의 의도 분류 결과 ("search_lessons" | "get_recommendations" | "manage_enrollment" | "faq_inquiry" | "general_inquiry" 등)

    # ── [3. 도구 실행 이력] 단일 에이전트 모드 호환용 정보 ──
    
    tool_name: Optional[str]
    # 현재 실행 또는 직전에 실행 완료된 도구 이름
    
    tool_args: Optional[Dict[str, Any]]
    # 도구 실행 시 주입된 파라미터 목록 (디버깅 및 로깅 용도)
    
    tool_result: Optional[Dict[str, Any]]
    # 도구의 반환 결과 데이터 (성공 여부 success 및 실제 데이터 data 포함)

    # ── [4. 검증 및 재시도] validator_node에 의해 업데이트 ──
    
    is_valid: bool
    # 도구 실행 결과 검증 통과 여부 (데이터 존재 여부 및 유효성 판단 결과)
    
    retry_count: int
    # 현재 도구의 재시도 누적 횟수 (지정된 임계값 도달 시 재시도 중단 및 응답 처리)
    
    retry_strategy: Optional[str]
    # 재시도 시 필터를 어떻게 해제할지 결정하는 전략 식별자

    # ── [5. 최종 결과 및 메트릭] ──
    
    response: str
    # 사용자에게 전달할 최종 자연어 응답 텍스트
    
    tools_used: List[str]
    # 이번 턴에 호출이 시도된 모든 도구/에이전트 이름 목록 (누적 기록)
    
    all_tool_results: Dict[str, Any]
    # 각 도구별 실행 결과 아카이브 (Langfuse 모니터링 및 디버깅용 수집 데이터)
    
    total_tokens: int
    # 이번 대화 턴 전체에서 소비된 LLM 총 토큰 수 (비용 추적용)
    
    error: Optional[str]
    # 실행 중 예외나 에러 발생 시 기록되는 메시지

    # ── [6. 멀티에이전트 라우팅 상태 정보] ──
    
    routing_mode: Literal["single_agent", "multi_agent", "direct_response"]
    # 시스템 실행 모드 (단일 에이전트, 멀티 에이전트, 즉시 응답)
    
    agent_plan: list[Literal["lesson", "enrollment", "faq", "facility"]]
    # 실행할 서브에이전트들의 순차적 계획 리스트
    
    current_agent_index: int
    # 현재 실행 중인 서브에이전트의 agent_plan 내 인덱스 위치
    
    agent_outputs: dict[str, dict]
    # 각 서브에이전트별 최종 실행 결과 딕셔너리
    
    handoff_reason: Optional[str]
    # 다음 서브에이전트로 제어권을 넘기게 된 사유(핸드오프 원인)
    
    rerouting_count: int
    # Supervisor에 의해 동적으로 재라우팅이 일어난 횟수
    
    rerouted_from: Optional[str]
    # 재라우팅을 트리거하고 실패했던 이전 에이전트의 이름


