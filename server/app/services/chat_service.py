import json
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Tuple
from langgraph.graph import StateGraph, END
from app.models.chat import ChatSession, ChatMessage
from app.models.ai_log import AILog
from app.services.ai.agent_state import AgentState
from app.services.ai.agent_nodes import (
    router_node,
    tool_executor_node,
    validator_node,
    response_node,
)
from app.services.ai.agent_graph import should_use_tool, should_retry_or_respond


class ChatService:
    
    @staticmethod
    async def get_or_create_session(
        db: AsyncSession,
        session_id: str,
        student_name: Optional[str] = None
    ) -> ChatSession:
        """세션 조회 또는 생성"""
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
        """메시지 저장"""
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
        """최근 메시지 조회"""
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
        """세션 목록"""
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
        """채팅 처리 메인"""
        
        start_time = time.time()
        
        # 1. 세션 생성/조회
        session = await ChatService.get_or_create_session(db, session_id, student_name)
        
        # 2. 사용자 메시지 저장
        user_msg = await ChatService.save_message(db, session_id, "user", user_message)
        
        # 3. 세션 제목 설정
        await ChatService.update_session_title(db, session_id, user_message)
        
        # 4. 대화 히스토리 조회
        history = await ChatService.get_recent_messages(db, session_id, limit=10)
        
        # 5. LangGraph 기반 Agent 실행 (멀티스텝)
        tools_used, all_tool_results, assistant_content, tokens_used = await ChatService._run_agent_graph(
            db, user_message, history, student_name or session.student_name
        )
        
        # 6. 어시스턴트 메시지 저장
        assistant_msg = await ChatService.save_message(
            db, session_id, "assistant", assistant_content,
            tool_used=",".join(tools_used) if tools_used else None,
            tool_result=all_tool_results if all_tool_results else None
        )
        
        # 7. AI 로그 저장
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
        
        return user_msg, assistant_msg
    
    @staticmethod
    async def _run_agent_graph(
        db: AsyncSession,
        user_message: str,
        history: List[ChatMessage],
        student_name: Optional[str]
    ) -> Tuple[List[str], dict, str, Optional[int]]:
        """
        LangGraph 기반 Agent 실행.

        Returns:
            - tools_used: 사용된 도구 목록
            - all_tool_results: 모든 도구 실행 결과
            - assistant_content: 최종 응답
            - tokens_used: 총 토큰 사용량
        """

        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history[:-1]
        ]

        initial_state: AgentState = {
            "user_message": user_message,
            "student_name": student_name,
            "chat_history": chat_history,
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

        try:
            async def tool_executor_with_db(state: AgentState):
                return await tool_executor_node(state, db)

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

            compiled = graph.compile()

            final_state: AgentState = await compiled.ainvoke(initial_state)

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
            return (
                [],
                {},
                "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                None,
            )
