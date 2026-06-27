"""
ChatOrchestrator 서비스 레이어.
사용자 세션 관리, 메시지 기록 영속화, AI 실행 로그 적재 및
LangGraph 멀티에이전트 파이프라인(비스트리밍 및 스트리밍) 구동을 전담한다.
"""

import datetime
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.ai_log import AILog
from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import response_node_stream
from app.services.ai.agent_graph import build_multi_agent_graph
from app.services.ai.langfuse_client import get_langfuse, flush_langfuse


class ChatOrchestrator:
    
    @staticmethod
    async def get_or_create_session(
        db: AsyncSession,
        session_id: str,
        student_name: Optional[str] = None
    ) -> ChatSession:
        """
        대화 세션을 조회하고, 없을 경우 신규 세션을 생성하여 DB에 영속화한다.
        - 세션이 이미 존재하지만 수강생 이름(student_name)이 누락되어 있을 경우 최신 정보로 업데이트한다.
        """
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            session = ChatSession(
                session_id=session_id,
                student_name=student_name
            )
            db.add(session)
            await db.commit()
            await db.refresh(session)
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
        """
        개별 대화 메시지(사용자 입력 및 AI 답변)를 영속 데이터베이스에 저장한다.
        - AI 답변일 경우 사용된 도구명(tool_used)과 상세 실행 결과(tool_result)를 함께 저장하여 관리 분석에 활용한다.
        """
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            tool_used=tool_used,
            tool_result=tool_result
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message
    
    @staticmethod
    async def get_recent_messages(
        db: AsyncSession,
        session_id: str,
        limit: int = 10
    ) -> List[ChatMessage]:
        """
        최근 N개의 대화 메시지를 조회하여 시간 순서대로 정렬해 반환한다.
        - AI 모델 호출 시 대화 맥락(Context)을 정확하게 복원하기 위해 시간 오름차순으로 정렬하여 반환한다.
        """
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(desc(ChatMessage.created_at))
            .limit(limit)
        )
        messages = list(result.scalars().all())
        return list(reversed(messages))
    
    @staticmethod
    async def get_sessions(db: AsyncSession, limit: int = 20) -> List[ChatSession]:
        """최근 대화방 목록을 업데이트 시간 역순으로 정렬하여 조회한다 (사이드바 대화 목록용)."""
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
        """특정 대화 세션의 모든 메시지 내역을 시간 오름차순으로 전체 조회한다."""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_session_title(db: AsyncSession, session_id: str, title: str):
        """대화방의 제목을 초기 설정한다. 기존 제목이 비어 있을 때 첫 메시지의 최대 50자까지만 추출하여 저장한다."""
        result = await db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()
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
        """
        비스트리밍 방식으로 사용자의 질문에 답변을 생성하고 전체 처리 프로세스를 조율한다.
        1. 대화방 조회/생성 및 사용자 메시지 DB 선저장
        2. AI 파이프라인 비스트리밍 호출 및 실행 결과(토큰, 레이턴시, 사용 도구) DB 적재
        3. Lazy-loading 만료 문제를 방지하기 위해 반환 객체 refresh 처리
        """
        start_time = time.time()
        
        session = await ChatOrchestrator.get_or_create_session(db, session_id, student_name)
        user_msg = await ChatOrchestrator.save_message(db, session_id, "user", user_message)
        await ChatOrchestrator.update_session_title(db, session_id, user_message)
        
        history = await ChatOrchestrator.get_recent_messages(db, session_id, limit=10)
        
        tools_used, all_tool_results, assistant_content, tokens_used = await ChatOrchestrator._run_agent_graph(
            db, user_message, history, student_name or session.student_name
        )
        
        assistant_msg = await ChatOrchestrator.save_message(
            db, session_id, "assistant", assistant_content,
            tool_used=",".join(tools_used) if tools_used else None,
            tool_result=all_tool_results if all_tool_results else None
        )
        
        # 관리자 통계 대시보드를 위한 원격 분석 로그 전송
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

        flush_langfuse()

        # 세션 커밋 과정에서 Assistant 메시지 객체가 만료될 수 있으므로 refresh 하여 속성 유실 방지
        await db.refresh(user_msg)
        await db.refresh(assistant_msg)

        return user_msg, assistant_msg

    @staticmethod
    async def chat_stream(
        db: AsyncSession,
        session_id: str,
        user_message: str,
        student_name: Optional[str] = None,
    ) -> AsyncGenerator[dict, None]:
        """
        스트리밍(SSE) 방식으로 토큰별 타이핑 효과를 유도하며 사용자 질문에 실시간 답변한다.
        - 실행 과정의 진행 상태(Status), 토큰 데이터(Token), 최종 결과 메트릭(Result/Done) 이벤트를 차례대로 생성하여 브라우저에 yield한다.
        """
        start_time = time.time()

        try:
            session = await ChatOrchestrator.get_or_create_session(
                db, session_id, student_name
            )

            await ChatOrchestrator.save_message(db, session_id, "user", user_message)
            await ChatOrchestrator.update_session_title(db, session_id, user_message)

            history = await ChatOrchestrator.get_recent_messages(
                db, session_id, limit=10
            )

            full_response = ""
            tools_used: List[str] = []
            all_tool_results: dict = {}
            total_tokens: int = 0

            # 비동기 제너레이터를 순회하며 SSE 이벤트 스트림 조립 및 클라이언트 전달
            async for event in ChatOrchestrator._run_agent_graph_stream(
                db,
                user_message,
                history,
                student_name or session.student_name,
            ):
                if event["type"] == "status":
                    yield {
                        "event": "status",
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
                elif event["type"] == "token":
                    full_response += event["data"]["content"]
                    yield {
                        "event": "token",
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
                elif event["type"] == "result":
                    tools_used = event["data"].get("tools_used", [])
                    all_tool_results = event["data"].get("all_tool_results", {})
                    total_tokens = event["data"].get("total_tokens", 0)
                    if not full_response:
                        full_response = event["data"].get("response", "")

            # 스트리밍 결과 최종 집합 저장
            assistant_msg = await ChatOrchestrator.save_message(
                db,
                session_id,
                "assistant",
                full_response,
                tool_used=",".join(tools_used) if tools_used else None,
                tool_result=all_tool_results if all_tool_results else None,
            )

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

            flush_langfuse()

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
        AI 에이전트 실행에 필요한 AgentState의 초기 필드를 규격화하여 선언한다.
        - history의 마지막 항목은 방금 저장된 현재 질문이므로 대화 역사 목록에서 배제 처리한다.
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
        비스트리밍 전용 LangGraph 그래프를 ainvoke()로 실행하고 최종 결과를 한 번에 리턴받는다.
        - Langfuse가 활성화된 경우 전체 에이전트 구동 라이프사이클을 감싸는 단일 루트 Span을 생성한다.
        """
        initial_state = ChatOrchestrator._build_initial_state(
            user_message, student_name, history
        )

        try:
            async def _execute_graph(state: AgentState) -> AgentState:
                state["_db"] = db
                compiled = build_multi_agent_graph()
                return await compiled.ainvoke(state)

            langfuse = get_langfuse()

            if langfuse:
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name="chat-agent",
                    input={
                        "user_message": user_message,
                        "student_name": student_name,
                    },
                ) as span:
                    trace_id = getattr(span, "id", None)
                    initial_state["trace_id"] = trace_id

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
        스트리밍 전용 LangGraph 그래프 구동을 시작하며 Langfuse 루트 Span을 인가한다.
        - 실제 세부 노드별 실행은 _run_agent_graph_stream_inner 측에 제어권을 위임한다.
        """
        initial_state = ChatOrchestrator._build_initial_state(
            user_message, student_name, history
        )

        langfuse = get_langfuse()

        try:
            if langfuse:
                with langfuse.start_as_current_observation(
                    as_type="span",
                    name="chat-agent-stream",
                    input={
                        "user_message": user_message,
                        "student_name": student_name,
                    },
                ) as span:
                    trace_id = getattr(span, "id", None)
                    initial_state["trace_id"] = trace_id

                    async for item in ChatOrchestrator._run_agent_graph_stream_inner(
                        db, initial_state, span
                    ):
                        yield item
            else:
                async for item in ChatOrchestrator._run_agent_graph_stream_inner(
                    db, initial_state, None
                ):
                    yield item

        except Exception as e:
            print(f"[LangGraph Stream] 에러: {e}")
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
        스트리밍 에이전트 상태 사전에 DB 세션을 동적 바인딩한 후, 멀티 에이전트 수동 오케스트레이션 함수를 기동한다.
        """
        state: AgentState = dict(initial_state)
        state["_db"] = db

        async for ev in ChatOrchestrator._run_multi_agent_stream(state, db, root_span):
            yield ev

    _AGENT_STATUS_MESSAGES: dict[str, str] = {
        "lesson": "강습 정보 찾는 중...",
        "enrollment": "수강 현황 확인 중...",
        "faq": "관련 정보 찾는 중...",
        "facility": "체육시설 찾는 중...",
        "calendar": "일정 확인 및 등록 중...",
    }

    @staticmethod
    async def _run_multi_agent_stream(
        state: AgentState,
        db: AsyncSession,
        root_span,
    ) -> AsyncGenerator[dict, None]:
        """
        스트리밍 동작을 위해 LangGraph의 Ainvoke() 호출 대신, 노드들을 순차적(Supervisor -> 서브에이전트 -> Response)으로 직접 순회 호출하는 오케스트레이터의 핵심 엔진.
        - 각 실행 상태(의도 분석, 특정 에이전트 구동, 재라우팅 폴백 등) 변화 시 진행 피드백을 실시간 브라우저로 샌딩한다.
        - 실패 시 1회 한정 교차 재라우팅(Rerouting) 및 최종 답변 스트리밍 토큰 청크 조립 처리를 모두 대행한다.
        """
        from app.services.ai.agents import (
            enrollment_agent,
            facility_agent,
            faq_agent,
            lesson_agent,
            calendar_agent,
        )
        from app.services.ai.routing_nodes import (
            aggregator_node,
            reroute_supervisor_node,
            supervisor_node,
        )
        
        _AGENT_REGISTRY = {
            "lesson": lesson_agent,
            "enrollment": enrollment_agent,
            "faq": faq_agent,
            "facility": facility_agent,
            "calendar": calendar_agent,
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
                        "message": ChatOrchestrator._AGENT_STATUS_MESSAGES.get(
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

        # ── 실패 시 1회 한정 대체 에이전트 재라우팅 ──
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

            # 재라우팅 후 새 agent_plan과 인덱스 읽기
            new_plan = state.get("agent_plan", []) or []
            new_idx = state.get("current_agent_index", 0)

            # 실행할 새 에이전트가 있으면
            if new_idx < len(new_plan):
                new_agent = new_plan[new_idx]
                agent_fn = _AGENT_REGISTRY.get(new_agent)
                if agent_fn is not None:
                    yield {
                        "type": "status",
                        "data": {
                            "step": "agent_start",
                            "agent": new_agent,
                            "message": ChatOrchestrator._AGENT_STATUS_MESSAGES.get(
                                new_agent, f"{new_agent} 실행 중..."
                            ),
                            "rerouted": True, # 재라우팅된 에이전트임을 프론트에 표시
                        },
                    }

                    # 새 에이전트 실행 → 결과 state에 저장
                    agent_result = await agent_fn(state)
                    state.update(agent_result)

                    # aggregator 실행 → is_valid 판정
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
                            "rerouted": True, # 재라우팅된 에이전트임을 프론트에 표시
                        },
                    }

        yield {
            "type": "status",
            "data": {"step": "response", "message": "답변 생성 중..."},
        }
        # 프론트에 "답변 생성 중..." 표시

        response_tokens = 0
        full_response = ""

        async for chunk in response_node_stream(state):
            if chunk["type"] == "token":
                full_response += chunk["content"] # GPT 토큰 조각을 전체 텍스트에 누적
                yield { # 토큰 조각을 프론트로 바로 전송 (타이핑 효과)
                    "type": "token",
                    "data": {"content": chunk["content"]},
                }
            elif chunk["type"] == "usage": # 스트림 마지막에 한 번 오는 토큰 사용량 기록
                response_tokens = chunk.get("total_tokens", 0)

        # 최종 응답과 누적 토큰 수 state에 저장
        state["response"] = full_response
        state["total_tokens"] = state.get("total_tokens", 0) + response_tokens

        if root_span is not None:
            try: # Langfuse 루트 span에 최종 응답 + 실행 메타데이터 기록
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
                "response": full_response, # 최종 자연어 응답
                "tools_used": state.get("tools_used", []), # 사용한 에이전트 목록
                "all_tool_results": state.get("all_tool_results", {}), # 모든 에이전트 결과
                "total_tokens": state.get("total_tokens", 0), # 총 토큰 사용량
            },
        }
