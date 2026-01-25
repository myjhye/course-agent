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
                    
                    # 수강생 이름 자동 주입 (강화)
                    if student_name:
                        if tool_name in ["get_my_enrollments", "get_recommendations"]:
                            # 항상 덮어쓰기 (LLM이 잘못된 이름 넣는 것 방지)
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
        
        name_instruction = ""
        if student_name:
            name_instruction = f"""
## 현재 수강생 정보
- 이름: {student_name}
- 이 정보를 이미 알고 있으므로 다시 묻지 마세요.
- get_my_enrollments, get_recommendations 호출 시 이 이름을 사용하세요.
"""
        else:
            name_instruction = """
## 수강생 정보
수강생 이름이 확인되지 않았습니다.
- 수강 현황이나 개인 추천을 요청하면 먼저 이름을 물어보세요.
"""

        return f"""당신은 스포츠 강습 플랫폼 'Course Agent'의 AI 상담사입니다.

{name_instruction}

## 도구 사용 가이드 (중요!)

### 1. search_lessons - 강습 검색
**반드시 사용해야 하는 경우:**
- 특정 종목 강습 요청: "수영 강습 알려줘", "테니스 배우고 싶어"
- 특정 조건 검색: "초급 요가", "성인 골프"
- "OO 강습 추천해줘"처럼 특정 종목이 언급된 경우

**파라미터:**
- sport_type: swimming(수영), tennis(테니스), golf(골프), yoga(요가), pilates(필라테스), fitness(피트니스)
- difficulty: beginner(입문), elementary(초급), intermediate(중급), advanced(고급)
- target_audience: adult(성인), child(어린이), senior(시니어)

### 2. get_recommendations - 맞춤 추천
**사용 시점:**
- "추천해줘", "뭐 들을까" 등 특정 종목 없이 추천 요청할 때
- "나한테 맞는 강습", "다음에 뭐 들으면 좋을까"

**주의:** 특정 종목이 언급되면 이 도구 대신 search_lessons 사용!

### 3. get_my_enrollments - 수강 현황
**사용 시점:** "내 수강 현황", "지금 뭐 듣고 있어", "수강 중인 강습"

### 4. get_lesson_detail - 강습 상세
**사용 시점:** 특정 강습의 상세 정보 요청 시 (ID 필요)

### 5. search_faq - FAQ 검색
**사용 시점:** 환불, 결제, 이용 방법 등 일반적인 질문

## 도구 선택 예시 (필독!)
- "수영 강습 추천해줘" → search_lessons(sport_type="swimming")
- "테니스 초급반 있어?" → search_lessons(sport_type="tennis", difficulty="beginner")
- "골프 배우고 싶어" → search_lessons(sport_type="golf")
- "추천 좀 해줘" → get_recommendations()
- "나한테 맞는 거 추천해줘" → get_recommendations()
- "내 수강 현황 알려줘" → get_my_enrollments()

## 응답 스타일
- 친근하고 격려하는 톤
- 이모지 적절히 사용
- 강습 정보는 구조화하여 보기 쉽게
- 마무리 문장으로 추가 도움 제안"""
