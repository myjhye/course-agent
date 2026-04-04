"""
채팅 서비스.

세션 관리, 메시지 저장, LangGraph 에이전트 실행을 조율한다.
비스트리밍(chat)과 SSE 스트리밍(chat_stream) 두 가지 경로를 제공하며,
AI 파이프라인 실행은 각 경로별 내부 메서드(_run_agent_graph / _run_agent_graph_stream)에서 담당한다.

주요 메서드:
- chat()                          : 비스트리밍 채팅 진입점. AI 응답이 다 만들어지면 한 번에 반환.
- chat_stream()                   : 스트리밍 채팅 진입점. 토큰이 생길 때마다 브라우저로 바로 전송.
- _build_initial_state()          : 두 경로가 공통으로 쓰는 에이전트 초기 상태값 생성.
- _run_agent_graph()              : 비스트리밍용 그래프 실행. 모든 노드가 끝난 뒤 결과를 한 번에 반환.
- _run_agent_graph_stream()       : 스트리밍용 Langfuse 측정 구간을 열고 실제 실행을 inner에 넘기는 래퍼.
- _run_agent_graph_stream_inner() : 실제 스트리밍 실행부. Router→Tool→Validator→Response 순으로 노드를 직접 호출하며 토큰을 하나씩 전송.
"""

import json
import time
from typing import List, Optional, Tuple, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from langgraph.graph import StateGraph, END

from app.models.chat import ChatSession, ChatMessage
from app.models.ai_log import AILog
from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import (
    router_node,
    tool_executor_node,
    validator_node,
    response_node,
    response_node_stream,
)
from app.services.ai.agent_graph import should_use_tool, should_retry_or_respond
from app.services.ai.langfuse_client import get_langfuse, flush_langfuse


class ChatService:
    
    @staticmethod
    async def get_or_create_session(
        db: AsyncSession,
        session_id: str,
        student_name: Optional[str] = None
    ) -> ChatSession:
        """세션 조회 또는 생성"""
        # session_id로 기존 대화방 조회. 없으면 None 반환
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        # 대화방 없으면 새로 생성 후 DB 저장
        if not session:
            session = ChatSession(
                session_id=session_id,
                student_name=student_name
            )
            db.add(session)
            await db.commit()
            # DB 자동 생성값(id, created_at) 다시 로드
            await db.refresh(session)
        # 대화방은 있는데 이름 없으면 이름만 업데이트
        elif student_name and not session.student_name:
            session.student_name = student_name
            await db.commit()
        
        return session
    
    @staticmethod
    async def save_message(
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        tool_used: Optional[str] = None,
        tool_result: Optional[dict] = None
    ) -> ChatMessage:
        """메시지 저장"""
        # ChatMessage 객체 생성 후 DB 저장
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_used=tool_used,
            tool_result=tool_result
        )
        db.add(message)
        await db.commit()
        # DB 자동 생성값(id, created_at) 다시 로드
        await db.refresh(message)
        return message
    
    @staticmethod
    async def get_recent_messages(
        db: AsyncSession,
        session_id: str,
        limit: int = 10
    ) -> List[ChatMessage]:
        """최근 메시지 조회"""
        # 최신순으로 limit개 조회 (최신 N개를 빠르게 가져오기 위해 desc 정렬)
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        messages = list(result.scalars().all())
        # GPT에 넘길 때 대화 순서가 맞아야 하므로 오래된순으로 뒤집기
        return list(reversed(messages))
    
    @staticmethod
    async def get_sessions(db: AsyncSession, limit: int = 20) -> List[ChatSession]:
        """세션 목록"""
        # 최근 업데이트된 순으로 세션 목록 조회 (좌측 탭 대화 목록용)
        result = await db.execute(
            select(ChatSession)
            .order_by(desc(ChatSession.updated_at))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def get_session_messages(
        db: AsyncSession,
        session_id: str
    ) -> List[ChatMessage]:
        """세션 전체 메시지"""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_session_title(db: AsyncSession, session_id: str, title: str):
        """세션 제목 업데이트"""
        # 세션 조회
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        # 제목이 없을 때만 첫 메시지를 제목으로 저장 (50자 제한)
        # 이미 제목 있으면 덮어쓰지 않음
        if session and not session.title:
            session.title = title[:50]
            await db.commit()
    
    @staticmethod
    async def chat(
        db: AsyncSession,
        session_id: str,
        user_message: str,
        student_name: Optional[str] = None
    ) -> Tuple[ChatMessage, ChatMessage]:
        """채팅 처리 메인"""
        
        # 전체 처리 시간 측정 시작 (AI 로그에 latency 기록용)
        start_time = time.time()
        
        # 1. 세션 생성/조회
        session = await ChatService.get_or_create_session(db, session_id, student_name)
        
        # 2. 유저 메시지 DB 저장 (AI 실행 전에 먼저 저장 - 오류나도 유저 메시지는 보존)
        user_msg = await ChatService.save_message(db, session_id, "user", user_message)
        
        # 3. 세션 제목이 없으면 첫 메시지로 설정
        await ChatService.update_session_title(db, session_id, user_message)
        
        # 4. 이전 대화 10개 로드 (GPT 맥락 제공용)
        history = await ChatService.get_recent_messages(db, session_id, limit=10)
        
        # 5. LangGraph AI 파이프라인 실행 (비스트리밍 - 결과 한 번에 반환)
        tools_used, all_tool_results, assistant_content, tokens_used = await ChatService._run_agent_graph(
            db, user_message, history, student_name or session.student_name
        )
        
        # 6. AI 답변 DB 저장 (어떤 도구 썼는지, 도구 결과도 같이 저장)
        assistant_msg = await ChatService.save_message(
            db, session_id, "assistant", assistant_content,
            tool_used=",".join(tools_used) if tools_used else None,
            tool_result=all_tool_results if all_tool_results else None
        )
        
        # 7. AI 사용 로그 저장 (관리자 대시보드 모니터링용)
        latency_ms = (time.time() - start_time) * 1000
        ai_log = AILog(
            feature_type="chat",
            input_data={
                "message": user_message,
                "student_name": student_name,
                "iteration_count": len(tools_used) if tools_used else 0
            },
            output_data={
                "response": assistant_content,
                "tools_used": tools_used,
                "is_multi_step": len(tools_used) > 1 if tools_used else False
            },
            tokens_used=tokens_used,
            latency_ms=latency_ms
        )
        db.add(ai_log)
        await db.commit()

        # 프로세스가 짧게 끝나도 Langfuse 버퍼에 남지 않도록, 요청 단위로 강제 flush한다
        flush_langfuse()

        # 유저 메시지 + AI 답변 반환
        return user_msg, assistant_msg

    @staticmethod
    async def chat_stream(
        db: AsyncSession,
        session_id: str,
        user_message: str,
        student_name: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        SSE 스트리밍 채팅.
        각 단계마다 event를 yield한다.

        이벤트 종류:
        - {"event": "status", "data": {"step": "router", ...}}
        - {"event": "token", "data": {"content": "..."}}
        - {"event": "done", "data": {"tools_used": [...], ...}}
        - {"event": "error", "data": {"message": "..."}}
        - {"event": "status", "data": {"step": "router_done", "intent": "..."}}
        """

        # 전체 처리 시간 측정 시작 (비스트리밍과 동일한 기준으로 모니터링하기 위함)
        start_time = time.time()

        try:
            # 1. 세션 생성/조회
            session = await ChatService.get_or_create_session(
                db, session_id, student_name
            )

            # 2. 사용자 메시지 저장
            await ChatService.save_message(db, session_id, "user", user_message)

            # 3. 세션 제목 설정
            await ChatService.update_session_title(db, session_id, user_message)

            # 4. 대화 히스토리 조회
            history = await ChatService.get_recent_messages(
                db, session_id, limit=10
            )

            # 스트리밍 중 토큰을 누적할 변수들 초기화
            full_response = ""
            tools_used: List[str] = []
            all_tool_results: dict = {}
            total_tokens: int = 0

            # 5. AI 파이프라인 실행 - 이벤트 타입별로 분기해서 브라우저로 전달
            # LangGraph 스트림에서 단계/토큰/최종 결과 이벤트를 순차적으로 소비한다
            async for event in ChatService._run_agent_graph_stream(
                db,
                user_message,
                history,
                student_name or session.student_name,
            ):
                if event["type"] == "status":
                    # "의도 분석 중...", "정보 검색 중..." 등 단계 안내를 브라우저로 전송
                    yield {
                        "event": "status",
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
                elif event["type"] == "token":
                    # 스트리밍 토큰 조각을 전체 텍스트에 누적 (마지막에 DB 저장용)
                    full_response += event["data"]["content"]
                    # GPT 토큰 조각을 브라우저로 바로 전송 (타이핑 효과)
                    yield {
                        "event": "token",   # SSE 이벤트 이름
                        "data": json.dumps(event["data"], ensure_ascii=False),  # JSON 문자열로 변환
                    }
                elif event["type"] == "result":
                    # 브라우저로 보내지 않고 저장용으로만 수집
                    tools_used = event["data"].get("tools_used", [])
                    all_tool_results = event["data"].get("all_tool_results", {})
                    total_tokens = event["data"].get("total_tokens", 0)
                    if not full_response:
                        full_response = event["data"].get("response", "")

            # 6. 스트리밍 다 끝나고 나서 전체 응답 DB 저장
            # (스트리밍 중간에 저장하면 텍스트가 잘리므로 반드시 끝나고 저장)
            assistant_msg = await ChatService.save_message(
                db,
                session_id,
                "assistant",
                full_response,
                tool_used=",".join(tools_used) if tools_used else None,
                tool_result=all_tool_results if all_tool_results else None,
            )

            # 7. AI 사용 로그 저장
            latency_ms = (time.time() - start_time) * 1000
            ai_log = AILog(
                feature_type="chat_stream",
                input_data={
                    "message": user_message,
                    "student_name": student_name,
                },
                output_data={
                    "response_length": len(full_response),
                    "tools_used": tools_used,
                },
                tokens_used=total_tokens,
                latency_ms=latency_ms,
            )
            db.add(ai_log)
            await db.commit()

            # 8. Langfuse 버퍼 즉시 전송
            flush_langfuse()

            # 9. 스트리밍 완료 신호 전송 (프론트에서 로딩 상태 해제)
            yield {
                "event": "done",
                "data": json.dumps(
                    {
                        "tools_used": tools_used,
                        "total_tokens": total_tokens,
                        "message_id": assistant_msg.id,
                    },
                    ensure_ascii=False,
                ),
            }

        except Exception as e:
            print(f"[ChatStream] 에러: {e}")
            # 예외 발생 시 에러 이벤트 전송 (빈 화면 방지)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)}, ensure_ascii=False),
            }
    
    @staticmethod
    def _build_initial_state(
        user_message: str,
        student_name: Optional[str],
        history: List[ChatMessage],
    ) -> AgentState:
        """
        비스트리밍/스트리밍 경로 공통 AgentState 초기값.
        history[:-1]: 마지막 항목은 방금 저장한 유저 메시지라 제외한다.
        trace_id는 Langfuse span 생성 후 호출 측에서 주입한다.
        """
        chat_history = [
            {"role": msg.role, "content": msg.content} for msg in history[:-1]
        ]
        return {
            "user_message": user_message,
            "student_name": student_name,
            "chat_history": chat_history,
            "trace_id": None,
            "intent": "",
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
            "is_valid": False,
            "retry_count": 0,
            "retry_strategy": None,
            "response": "",
            "tools_used": [],
            "all_tool_results": {},
            "total_tokens": 0,
            "error": None,
        }

    @staticmethod
    async def _run_agent_graph(
        db: AsyncSession,
        user_message: str,
        history: List[ChatMessage],
        student_name: Optional[str]
    ) -> Tuple[List[str], dict, str, Optional[int]]:
        """
        비스트리밍 채팅 전용 LangGraph Agent 실행.
        chat()에서만 호출되며, compiled.ainvoke()로 결과를 한 번에 반환한다.
        스트리밍 경로는 _run_agent_graph_stream()을 사용한다.

        Returns:
            - tools_used: 사용된 도구 목록
            - all_tool_results: 모든 도구 실행 결과
            - assistant_content: 최종 응답
            - tokens_used: 총 토큰 사용량
        """

        initial_state = ChatService._build_initial_state(
            user_message, student_name, history
        )

        try:
            async def tool_executor_with_db(state: AgentState):
                return await tool_executor_node(state, db)

            # tool_executor_node가 현재 요청의 db 세션을 클로저로 캡처해야 하므로
            # 그래프를 전역 싱글톤으로 재사용하지 않고 요청마다 새로 조립한다.
            graph = StateGraph(AgentState)
            graph.add_node("router", router_node)
            graph.add_node("tool_executor", tool_executor_with_db)
            graph.add_node("validator", validator_node)
            graph.add_node("response", response_node)

            graph.set_entry_point("router")

            graph.add_conditional_edges(
                "router",
                should_use_tool,
                {"tool_executor": "tool_executor", "response": "response"},
            )
            graph.add_edge("tool_executor", "validator")
            graph.add_conditional_edges(
                "validator",
                should_retry_or_respond,
                {"tool_executor": "tool_executor", "response": "response"},
            )
            graph.add_edge("response", END)

            compiled = graph.compile()  # 실행 가능한 그래프로 컴파일

            langfuse = get_langfuse()
            root_span = None

            if langfuse:
                # LangGraph 전체 실행을 하나의 루트 span으로 감싼다.
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name="chat-agent",
                    input={
                        "user_message": user_message,
                        "student_name": student_name,
                    },
                ) as span:
                    root_span = span
                    trace_id = getattr(span, "id", None)
                    # 노드들이 같은 trace에 묶이도록 trace_id를 state에 주입
                    initial_state["trace_id"] = trace_id

                    # 비스트리밍: 모든 노드 실행 완료 후 최종 state 한 번에 반환
                    final_state: AgentState = await compiled.ainvoke(initial_state)

                    tools_used = final_state.get("tools_used", []) or []

                    span.update(
                        output={
                            "response": final_state.get(
                                "response",
                                "죄송합니다. 응답 생성에 실패했습니다.",
                            ),
                            "tools_used": tools_used,
                        },
                        metadata={
                            "iteration_count": len(tools_used),
                            "student_name": student_name,
                        },
                    )
            else:
                final_state = await compiled.ainvoke(initial_state)

            # 최종 state에서 필요한 값만 꺼내서 반환
            return (
                final_state.get("tools_used", []),
                final_state.get("all_tool_results", {}),
                final_state.get(
                    "response",
                    "죄송합니다. 응답 생성에 실패했습니다.",
                ),
                final_state.get("total_tokens"),
            )

        except Exception as e:
            print(f"[LangGraph] Agent 실행 에러: {e}")

            # Langfuse trace에 오류 정보 기록 (있을 경우에만)
            try:
                langfuse = get_langfuse()
                if langfuse:
                    with langfuse.start_as_current_observation(
                        as_type="span",
                        name="chat-agent-error",
                        input={"user_message": user_message},
                    ) as span:
                        span.update(
                            output=f"Error: {str(e)}",
                            level="ERROR",
                            status_message=str(e),
                        )
            except Exception:
                pass

            return (
                [],
                {},
                "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                None,
            )

    @staticmethod
    async def _run_agent_graph_stream(
        db: AsyncSession,
        user_message: str,
        history: List[ChatMessage],
        student_name: Optional[str],
    ) -> AsyncGenerator[dict, None]:
        """
        Langfuse 루트 span을 열고 _run_agent_graph_stream_inner를 실행한다.
        전체 AI 파이프라인을 하나의 span으로 묶어 Langfuse에서 end-to-end 추적이 가능하게 한다.
        """

        initial_state = ChatService._build_initial_state(
            user_message, student_name, history
        )

        langfuse = get_langfuse()

        try:
            if langfuse:
                # 스트리밍 버전 전용 루트 span
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name="chat-agent-stream",
                    input={
                        "user_message": user_message,
                        "student_name": student_name,
                    },
                ) as span:
                    trace_id = getattr(span, "id", None)
                    # 노드들이 같은 trace에 묶이도록 trace_id를 state에 주입
                    initial_state["trace_id"] = trace_id

                    # 실제 실행은 _run_agent_graph_stream_inner에 위임, 결과 그대로 올림
                    async for item in ChatService._run_agent_graph_stream_inner(
                        db, initial_state, span
                    ):
                        yield item
            else:
                # Langfuse 없으면 바로 실행
                async for item in ChatService._run_agent_graph_stream_inner(
                    db, initial_state, None
                ):
                    yield item

        except Exception as e:
            print(f"[LangGraph Stream] 에러: {e}")
            # 에러 발생 시 result 타입으로 fallback 응답 반환
            yield {
                "type": "result",
                "data": {
                    "response": "죄송합니다. 일시적인 오류가 발생했습니다.",
                    "tools_used": [],
                    "all_tool_results": {},
                    "total_tokens": 0,
                },
            }

    @staticmethod
    async def _run_agent_graph_stream_inner(
        db: AsyncSession,
        initial_state: AgentState,
        root_span,
    ) -> AsyncGenerator[dict, None]:
        """
        LangGraph 파이프라인을 단계별로 직접 실행하면서 SSE로 스트리밍한다.
        Router → ToolExecutor → Validator는 비스트리밍으로 실행하고,
        Response만 stream=True로 토큰을 yield한다.
        """

        # initial_state를 복사해 작업용 state로 쓴다.
        # dict()로 얕은 복사를 하는 이유는, 여러 번 재사용될 수 있는 initial_state를
        # 오염시키지 않고 이 실행 컨텍스트에 한정된 변경만 반영하기 위함이다.
        state: AgentState = dict(initial_state)

        # ── Phase 1: Router ──
        # 먼저 프론트에 "의도 분석 중" 상태를 보내 사용자에게 진행 상황을 알린다.
        yield {
            "type": "status",
            "data": {"step": "router", "message": "의도 분석 중..."},
        }

        # Router 노드에서 GPT-4o-mini가 사용자의 문장을 5가지 intent 중 하나로 분류한다.
        # 예: {"intent": "faq_inquiry", "total_tokens": 85}
        router_result = await router_node(state)

        # Router 결과를 state에 병합해, 이후 단계에서 intent와 total_tokens를 참고할 수 있게 한다.
        state.update(router_result)

        intent = state["intent"]

        # 어떤 intent로 분류됐는지 프론트에 알려 준다.
        # 이 정보는 UX(상태 표시)뿐 아니라 디버깅 시 "왜 이 툴을 탔는지"를 이해하는 데 도움이 된다.
        yield {
            "type": "status",
            "data": {"step": "router_done", "intent": intent},
        }

        # ── Phase 2: Tool Execution ──
        # general_inquiry(안녕하세요/감사 인사 등)는 비즈니스 툴 호출이 필요 없으므로
        # 바로 Response 단계로 넘어가 토큰 사용량을 줄인다.
        if intent != "general_inquiry":
            yield {
                "type": "status",
                "data": {"step": "tool_executor", "message": "정보 검색 중..."},
            }

            # ToolExecutor 노드는 intent에 맞는 도구(search_lessons, search_faq 등)를 선택하고 실행한다.
            # 결과에는 tool_name, tool_args, tool_result, tools_used 등이 포함된다.
            tool_result = await tool_executor_node(state, db)
            state.update(tool_result)

            # ── Phase 3: Validator ──
            # Validator 노드는 도구 실행 결과가 충분한지 검사하고,
            # 필요하면 retry_count와 retry_strategy를 설정해 재시도 정책을 결정한다.
            validator_result = await validator_node(state)
            state.update(validator_result)

            # Self-Correction: 검색 결과가 없을 때 필터를 완화해 자동 재검색한다.
            # 예) "고급 배드민턴 강습" → 결과 없음 → difficulty 필터 제거 → 입문/초급 강습 제안.
            # retry_count가 0이면 첫 시도가 성공한 것이므로 재시도하지 않고,
            # 2회를 넘기면 더 이상 조건을 완화해도 품질이 떨어질 수 있어 중단한다.
            if (
                not state["is_valid"]
                and state["retry_count"] > 0
                and state["retry_count"] <= 2
            ):
                yield {
                    "type": "status",
                    "data": {
                        "step": "retry",
                        "message": "조건 완화 재검색 중...",
                    },
                }
                # retry_strategy가 "relax_filters"인 경우, tool_executor_node 내부에서
                # 난이도/타겟 필터를 제거하고 sport_type+키워드만으로 재검색하도록 동작한다.
                tool_result = await tool_executor_node(state, db)
                state.update(tool_result)
                validator_result = await validator_node(state)
                state.update(validator_result)

        # ── Phase 4: Response (스트리밍) ──
        # 여기서부터 OpenAI `stream=True`를 통해 토큰을 하나씩 받아 프론트에 중계한다.
        # 사용자는 "답변 생성 중..." 메시지 이후 글자가 한 글자씩 타이핑되는 경험을 하게 된다.
        yield {
            "type": "status",
            "data": {"step": "response", "message": "답변 생성 중..."},
        }

        response_tokens = 0
        full_response = ""

        # response_node_stream은 OpenAI 스트리밍 응답을 래핑해
        # {"type": "token", "content": "..."} / {"type": "usage", "total_tokens": N}
        # 형태로 토큰과 사용량 정보를 전달한다.
        async for chunk in response_node_stream(state):
            if chunk["type"] == "token":
                full_response += chunk["content"]
                # 프론트의 onToken 콜백이 이 이벤트를 받아, 마지막 assistant 메시지에 문자열을 append한다.
                yield {
                    "type": "token",
                    "data": {"content": chunk["content"]},
                }
            elif chunk["type"] == "usage":
                # OpenAI의 `stream_options={"include_usage": True}` 설정 덕분에
                # 마지막 청크에서만 total_tokens 정보가 제공된다.
                response_tokens = chunk.get("total_tokens", 0)

        # 스트리밍이 끝난 시점의 최종 응답 텍스트와 토큰 수를 state에 반영한다.
        state["response"] = full_response
        state["total_tokens"] = state.get("total_tokens", 0) + response_tokens

        # Langfuse 루트 span이 존재하면, 최종 응답과 메타데이터를 업데이트해 Trace 뷰에서 볼 수 있게 한다.
        if root_span is not None:
            try:
                tools_used = state.get("tools_used", []) or []
                root_span.update(
                    output={"response": full_response, "tools_used": tools_used},
                    metadata={
                        "intent": state.get("intent"),
                        "iteration_count": len(tools_used),
                        "total_tokens": state.get("total_tokens"),
                    },
                )
            except Exception:
                # 관측 시스템 장애가 사용자 응답 흐름에 영향을 주면 안 되므로, 예외는 조용히 무시한다.
                pass

        # 최종 결과 이벤트는 chat_stream()에서 수집되어
        # DB에 assistant 메시지와 AILog를 저장하는 데 사용된다.
        yield {
            "type": "result",
            "data": {
                "response": full_response,
                "tools_used": state.get("tools_used", []),
                "all_tool_results": state.get("all_tool_results", {}),
                "total_tokens": state.get("total_tokens", 0),
            },
        }
