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
- _run_agent_graph_stream_inner() : 실제 스트리밍 실행부. 멀티에이전트 수동 오케스트레이션(_run_multi_agent_stream)으로 토큰을 전송.
"""

import json
import time
from typing import List, Optional, Tuple, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.chat import ChatSession, ChatMessage
from app.models.ai_log import AILog
from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import response_node_stream
from app.services.ai.agent_graph import build_multi_agent_graph
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

        # 긴 에이전트 실행 + 여러 차례의 commit 후 user_msg/assistant_msg는 expire 상태일 수 있다.
        # 라우터 레이어의 Pydantic model_validate가 속성을 읽을 때 lazy-load로 인한
        # MissingGreenlet 에러를 방지하기 위해 명시적으로 refresh한다.
        await db.refresh(user_msg)
        await db.refresh(assistant_msg)

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
        - {"event": "status", "data": {"step": "supervisor", "message": "..."}}
        - {"event": "status", "data": {"step": "supervisor_done", "mode": "...", "agents": [...]}}
        - {"event": "status", "data": {"step": "agent_start", "agent": "lesson|enrollment|faq|facility", "message": "..."}}  # 재라우팅 시 rerouted: true
        - {"event": "status", "data": {"step": "agent_done", "agent": "...", "success": true|false}}  # 재라우팅 시 rerouted: true
        - {"event": "status", "data": {"step": "reroute", "from": "...", "message": "..."}}
        - {"event": "status", "data": {"step": "response", "message": "..."}}
        - {"event": "token", "data": {"content": "..."}}
        - {"event": "done", "data": {"tools_used": [...], "total_tokens": ..., "message_id": ...}}
        - {"event": "error", "data": {"message": "..."}}
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
            async def _execute_graph(state: AgentState) -> AgentState:
                state["_db"] = db
                compiled = build_multi_agent_graph()
                return await compiled.ainvoke(state)

            langfuse = get_langfuse()

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
                    trace_id = getattr(span, "id", None)
                    # 노드들이 같은 trace에 묶이도록 trace_id를 state에 주입
                    initial_state["trace_id"] = trace_id

                    # 비스트리밍: 모든 노드 실행 완료 후 최종 state 한 번에 반환
                    final_state: AgentState = await _execute_graph(initial_state)

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
                final_state: AgentState = await _execute_graph(initial_state)

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
        SSE 스트리밍으로 멀티에이전트 파이프라인을 실행한다.
        Supervisor → 서브에이전트 → Aggregator → response_node_stream 순으로
        _run_multi_agent_stream에서 오케스트레이션한다.
        """

        state: AgentState = dict(initial_state)
        state["_db"] = db
        async for ev in ChatService._run_multi_agent_stream(state, db, root_span):
            yield ev

    _AGENT_STATUS_MESSAGES: dict[str, str] = {
        "lesson": "강습 정보 찾는 중...",
        "enrollment": "수강 현황 확인 중...",
        "faq": "관련 정보 찾는 중...",
        "facility": "체육시설 찾는 중...",
    }

    @staticmethod
    async def _run_multi_agent_stream(
        state: AgentState,
        db: AsyncSession,
        root_span,
    ) -> AsyncGenerator[dict, None]:
        """
        멀티에이전트 흐름을 수동 오케스트레이션으로 스트리밍한다.

        구조:
          1. supervisor_node 실행 (LLM, 토큰 사용)
          2. routing_mode에 따라 분기
             - direct_response: 바로 response_node_stream
             - single_agent/multi_agent: agent_plan 순회하며 각 에이전트 실행,
               매 회차마다 aggregator_node로 state 갱신
          3. response_node_stream으로 최종 응답 스트리밍

        각 단계에서 status 이벤트를 yield하여 프론트 로딩 UX를 유지한다.
        에이전트 실행 자체는 make_subagent가 반환한 함수 호출로 이루어지며,
        함수 반환 dict를 state에 merge하는 방식으로 langgraph ainvoke와 동일한 의미론을 수동 재현한다.
        """
        from app.services.ai.agents import (
            enrollment_agent,
            facility_agent,
            faq_agent,
            lesson_agent,
        )
        from app.services.ai.supervisor_node import (
            aggregator_node,
            reroute_supervisor_node,
            supervisor_node,
        )

        _AGENT_REGISTRY = {
            "lesson": lesson_agent,
            "enrollment": enrollment_agent,
            "faq": faq_agent,
            "facility": facility_agent,
        }

        yield {
            "type": "status",
            "data": {"step": "supervisor", "message": "의도 분석 중..."},
        }
        supervisor_result = await supervisor_node(state)
        state.update(supervisor_result)

        yield {
            "type": "status",
            "data": {
                "step": "supervisor_done",
                "mode": state.get("routing_mode"),
                "agents": state.get("agent_plan", []),
            },
        }

        plan = state.get("agent_plan", []) or []
        mode = state.get("routing_mode", "direct_response")

        if mode != "direct_response":
            for idx, agent_name in enumerate(plan):
                agent_fn = _AGENT_REGISTRY.get(agent_name)
                if agent_fn is None:
                    continue

                yield {
                    "type": "status",
                    "data": {
                        "step": "agent_start",
                        "agent": agent_name,
                        "message": ChatService._AGENT_STATUS_MESSAGES.get(
                            agent_name, f"{agent_name} 실행 중..."
                        ),
                    },
                }

                state["current_agent_index"] = idx

                agent_result = await agent_fn(state)
                state.update(agent_result)

                agg_result = aggregator_node(state)
                state.update(agg_result)

                yield {
                    "type": "status",
                    "data": {
                        "step": "agent_done",
                        "agent": agent_name,
                        "success": bool(
                            (state.get("agent_outputs") or {})
                            .get(agent_name, {})
                            .get("success")
                        ),
                    },
                }

        # ── 재라우팅 (single_agent + is_valid=False일 때 1회 시도) ──
        # for 루프 종료 후 aggregator가 반영한 state 기준. should_continue_after_aggregator와 동일 의미론.
        if (
            state.get("routing_mode") == "single_agent"
            and not state.get("is_valid", False)
            and state.get("rerouting_count", 0) == 0
        ):
            yield {
                "type": "status",
                "data": {
                    "step": "reroute",
                    "from": state.get("agent_plan", [])[-1]
                    if state.get("agent_plan")
                    else None,
                    "message": "다른 방식으로 다시 찾아보는 중...",
                },
            }

            reroute_result = reroute_supervisor_node(state)
            state.update(reroute_result)

            new_plan = state.get("agent_plan", []) or []
            new_idx = state.get("current_agent_index", 0)

            if new_idx < len(new_plan):
                new_agent = new_plan[new_idx]
                agent_fn = _AGENT_REGISTRY.get(new_agent)
                if agent_fn is not None:
                    yield {
                        "type": "status",
                        "data": {
                            "step": "agent_start",
                            "agent": new_agent,
                            "message": ChatService._AGENT_STATUS_MESSAGES.get(
                                new_agent, f"{new_agent} 실행 중..."
                            ),
                            "rerouted": True,
                        },
                    }

                    agent_result = await agent_fn(state)
                    state.update(agent_result)

                    agg_result = aggregator_node(state)
                    state.update(agg_result)

                    yield {
                        "type": "status",
                        "data": {
                            "step": "agent_done",
                            "agent": new_agent,
                            "success": bool(
                                (state.get("agent_outputs") or {})
                                .get(new_agent, {})
                                .get("success")
                            ),
                            "rerouted": True,
                        },
                    }

        yield {
            "type": "status",
            "data": {"step": "response", "message": "답변 생성 중..."},
        }

        response_tokens = 0
        full_response = ""

        async for chunk in response_node_stream(state):
            if chunk["type"] == "token":
                full_response += chunk["content"]
                yield {
                    "type": "token",
                    "data": {"content": chunk["content"]},
                }
            elif chunk["type"] == "usage":
                response_tokens = chunk.get("total_tokens", 0)

        state["response"] = full_response
        state["total_tokens"] = state.get("total_tokens", 0) + response_tokens

        if root_span is not None:
            try:
                tools_used = state.get("tools_used", []) or []
                root_span.update(
                    output={"response": full_response, "tools_used": tools_used},
                    metadata={
                        "routing_mode": state.get("routing_mode"),
                        "agent_plan": state.get("agent_plan"),
                        "iteration_count": len(tools_used),
                        "total_tokens": state.get("total_tokens"),
                    },
                )
            except Exception:
                pass

        yield {
            "type": "result",
            "data": {
                "response": full_response,
                "tools_used": state.get("tools_used", []),
                "all_tool_results": state.get("all_tool_results", {}),
                "total_tokens": state.get("total_tokens", 0),
            },
        }
