import json
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from app.models.chat import ChatSession, ChatMessage
from app.models.ai_log import AILog
from app.services.ai.llm_client import get_openai_client
from app.services.ai.tools import CHAT_TOOLS, NO_RESULT_MESSAGES
from app.services.ai.tool_executor import ToolExecutor


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
        """최근 메시지 조회 (대화 메모리)"""
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
    ) -> tuple[ChatMessage, ChatMessage]:
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
        
        # 5. Agent 실행
        tool_used, tool_result, assistant_content, tokens_used = await ChatService._run_agent(
            db, user_message, history, student_name or session.student_name
        )
        
        # 6. 어시스턴트 메시지 저장
        assistant_msg = await ChatService.save_message(
            db, session_id, "assistant", assistant_content,
            tool_used=tool_used,
            tool_result=tool_result
        )
        
        # 7. AI 로그 저장
        latency_ms = (time.time() - start_time) * 1000
        ai_log = AILog(
            feature_type="chat",
            input_data={"message": user_message, "student_name": student_name},
            output_data={"response": assistant_content, "tool_used": tool_used},
            tokens_used=tokens_used,
            latency_ms=latency_ms
        )
        db.add(ai_log)
        await db.commit()
        
        return user_msg, assistant_msg
    
    @staticmethod
    async def _run_agent(
        db: AsyncSession,
        user_message: str,
        history: List[ChatMessage],
        student_name: Optional[str]
    ) -> tuple[Optional[str], Optional[dict], str, Optional[int]]:
        """Agent 실행"""
        
        client = get_openai_client()
        executor = ToolExecutor(db)
        
        # 시스템 프롬프트
        system_prompt = f"""당신은 스포츠 강습 플랫폼의 친절한 AI 상담사입니다.

반드시 제공된 도구를 사용해서 정보를 조회한 후 답변하세요.
- 강습 검색/추천 → search_lessons 사용
- 강습 상세 정보 → get_lesson_detail 사용
- 수강 현황 → get_my_enrollments 사용
- 강습 추천 → get_recommendations 사용
- 환불/결제/이용방법 → search_faq 사용

중요 규칙:
1. 도구 조회 결과에 있는 정보만 답변하세요.
2. 조회 결과가 없으면 "찾을 수 없다"고 정직하게 말하세요.
3. 추측하거나 지어내지 마세요.

응답 스타일:
- 항상 인사 또는 도입 문장으로 시작하세요.
- 정보를 전달한 후 마무리 문장을 추가하세요.
- 친근하고 따뜻한 톤을 유지하세요.

응답 형식 예시:

[수강 현황 조회]
{student_name}님의 수강 현황을 안내해드릴게요! 😊

---

현재 총 1개의 강습을 수강하고 계세요.

📚 수강 중인 강습

- 강습명: 성인 수영 입문반
- 상태: 수강 중
- 출석률: 88%

---

더 궁금한 사항이 있으시면 언제든지 말씀해 주세요!

[강습 검색]
요청하신 강습을 찾아봤어요!

---

🔍 검색 결과 (2건)

1. 성인 수영 입문반
   종목: 수영 | 난이도: 입문 | 강사: 김수영

2. 성인 수영 초급반
   종목: 수영 | 난이도: 초급 | 강사: 김수영

---

관심 있는 강습이 있으시면 더 자세히 알려드릴게요!

[FAQ]
문의하신 내용에 대해 안내드릴게요.

---

(FAQ 내용)

---

추가로 궁금한 점이 있으시면 편하게 물어봐주세요! 😊

{f"현재 수강생: {student_name}" if student_name else "수강생 정보가 없습니다. 필요시 이름을 물어보세요."}"""

        # 메시지 구성
        messages = [{"role": "system", "content": system_prompt}]
        
        for msg in history[:-1]:  # 마지막(현재 user 메시지) 제외
            messages.append({"role": msg.role, "content": msg.content})
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            # 1차 호출: 도구 사용 여부 판단
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=CHAT_TOOLS,
                tool_choice="auto",
                max_tokens=1000
            )
            
            assistant_message = response.choices[0].message
            tokens_used = response.usage.total_tokens if response.usage else None
            
            # 도구 호출이 있는 경우
            if assistant_message.tool_calls:
                tool_call = assistant_message.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                # 수강생 이름 자동 주입
                if student_name and "student_name" in tool_args:
                    pass  # 이미 있음
                elif student_name and tool_name in ["get_my_enrollments", "get_recommendations"]:
                    tool_args["student_name"] = student_name
                
                # 도구 실행
                tool_result = await executor.execute(tool_name, tool_args)
                
                # 결과가 없는 경우
                if not tool_result.get("success"):
                    no_result_msg = NO_RESULT_MESSAGES.get(tool_name, NO_RESULT_MESSAGES["no_tool"])
                    if "{keyword}" in no_result_msg:
                        no_result_msg = no_result_msg.format(keyword=tool_args.get("keyword", ""))
                    return tool_name, tool_result, no_result_msg, tokens_used
                
                # 2차 호출: 도구 결과로 자연어 응답 생성
                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_args, ensure_ascii=False)
                            }
                        }
                    ]
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })
                
                final_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=1000
                )
                
                final_tokens = final_response.usage.total_tokens if final_response.usage else 0
                total_tokens = (tokens_used or 0) + final_tokens
                
                return tool_name, tool_result, final_response.choices[0].message.content, total_tokens
            
            # 도구 호출 없이 직접 답변 (지양)
            if assistant_message.content:
                return None, None, assistant_message.content, tokens_used
            
            return None, None, NO_RESULT_MESSAGES["no_tool"], tokens_used
            
        except Exception as e:
            print(f"Chat error: {e}")
            return None, None, "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.", None

