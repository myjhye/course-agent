import json
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional, Tuple
from app.models.chat import ChatSession, ChatMessage
from app.models.ai_log import AILog
from app.services.ai.llm_client import get_openai_client
from app.services.ai.tools import CHAT_TOOLS, NO_RESULT_MESSAGES
from app.services.ai.tool_executor import ToolExecutor


MAX_ITERATIONS = 5  # 무한 루프 방지


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
        
        # 5. Agent 루프 실행 (멀티스텝)
        tools_used, all_tool_results, assistant_content, tokens_used = await ChatService._run_agent_loop(
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
    async def _run_agent_loop(
        db: AsyncSession,
        user_message: str,
        history: List[ChatMessage],
        student_name: Optional[str]
    ) -> Tuple[List[str], dict, str, Optional[int]]:
        """
        Agent 루프 실행 (멀티스텝 오케스트레이션)
        
        Returns:
            - tools_used: 사용된 도구 목록
            - all_tool_results: 모든 도구 실행 결과
            - assistant_content: 최종 응답
            - tokens_used: 총 토큰 사용량
        """
        
        client = get_openai_client()
        executor = ToolExecutor(db)
        
        # 시스템 프롬프트
        system_prompt = ChatService._build_system_prompt(student_name)
        
        # 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[:-1]:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": user_message})
        
        # Agent 상태
        tools_used = []
        all_tool_results = {}
        total_tokens = 0
        iteration = 0
        
        try:
            while iteration < MAX_ITERATIONS:
                iteration += 1
                
                # LLM 호출
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=CHAT_TOOLS,
                    tool_choice="auto",
                    max_tokens=1500
                )
                
                assistant_message = response.choices[0].message
                total_tokens += response.usage.total_tokens if response.usage else 0
                
                # 도구 호출이 없으면 종료
                if not assistant_message.tool_calls:
                    # 최종 응답 반환
                    final_content = assistant_message.content or NO_RESULT_MESSAGES["no_tool"]
                    return tools_used, all_tool_results, final_content, total_tokens
                
                # 도구 호출 처리 (여러 도구 동시 호출 지원)
                tool_messages = []
                
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # 수강생 이름 자동 주입
                    if student_name and tool_name in ["get_my_enrollments", "get_recommendations"]:
                        if "student_name" not in tool_args:
                            tool_args["student_name"] = student_name
                    
                    # 도구 실행
                    tool_result = await executor.execute(tool_name, tool_args)
                    
                    # 결과 저장
                    tools_used.append(tool_name)
                    all_tool_results[f"{tool_name}_{iteration}"] = tool_result
                    
                    # 메시지에 도구 결과 추가
                    tool_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })
                
                # Assistant 메시지 + 도구 결과를 대화에 추가
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })
                messages.extend(tool_messages)
                
                # 다음 반복에서 LLM이 추가 도구가 필요한지 판단
            
            # MAX_ITERATIONS 도달 시
            return tools_used, all_tool_results, "죄송합니다. 요청을 처리하는 데 문제가 발생했습니다.", total_tokens
            
        except Exception as e:
            print(f"Agent loop error: {e}")
            return [], {}, "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", None
    
    @staticmethod
    def _build_system_prompt(student_name: Optional[str]) -> str:
        """시스템 프롬프트 생성"""
        return f"""당신은 스포츠 강습 플랫폼의 친절한 AI 상담사입니다.

## 도구 사용 규칙
반드시 제공된 도구를 사용해서 정보를 조회한 후 답변하세요.
- search_lessons: 강습 검색
- get_lesson_detail: 강습 상세 정보
- get_my_enrollments: 수강 현황 조회
- get_recommendations: 강습 추천
- search_faq: FAQ 검색

## 멀티스텝 처리
복잡한 질문은 여러 도구를 순차적으로 사용하세요.

예시 1: "내가 들은 강습 요약하고 다음 추천해줘"
→ get_my_enrollments로 수강 현황 조회
→ get_recommendations로 추천 강습 조회
→ 두 결과를 종합해서 응답

예시 2: "수영 강습 중에 초급 있어? 있으면 자세히 알려줘"
→ search_lessons로 수영 초급 검색
→ 결과가 있으면 get_lesson_detail로 상세 조회
→ 종합 응답

예시 3: "환불 규정 알려주고, 내 수강 상태도 확인해줘"
→ search_faq로 환불 규정 조회
→ get_my_enrollments로 수강 상태 조회
→ 두 정보를 함께 응답

## 응답 규칙
1. 도구 조회 결과에 있는 정보만 답변하세요.
2. 조회 결과가 없으면 "찾을 수 없다"고 정직하게 말하세요.
3. 추측하거나 지어내지 마세요.
4. 여러 정보를 조회했으면 체계적으로 정리해서 응답하세요.

## 응답 스타일
- 항상 인사 또는 도입 문장으로 시작하세요.
- 정보가 여러 개면 섹션을 나눠서 정리하세요.
- 마무리 문장을 추가하세요.
- 친근하고 따뜻한 톤을 유지하세요.
- 이모지를 적절히 사용하세요.

## 응답 형식 예시

[수강 현황 + 추천 조합]
{student_name}님의 수강 현황과 추천 강습을 안내해드릴게요! 😊

📚 현재 수강 현황
총 2개의 강습을 수강하고 계세요.

- 성인 수영 입문반 - 수강 완료 ✅ (출석률 95%)
- 성인 수영 초급반 - 수강 중 (출석률 80%)

✨ 맞춤 추천 강습
수강 이력을 바탕으로 추천드려요!

1. 성인 수영 중급반
   → 초급반을 잘 마치시면 자연스럽게 도전해보세요!

2. 성인 테니스 입문반
   → 새로운 종목도 도전해보시는 건 어떨까요?

꾸준히 열심히 하고 계시네요! 화이팅입니다! 💪

{f"현재 수강생: {student_name}" if student_name else "수강생 정보가 없습니다. 필요시 이름을 물어보세요."}"""
