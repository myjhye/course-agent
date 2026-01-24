import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ai.llm_client import generate_text
from app.models.feedback import Feedback
from app.models.enrollment import Enrollment
from app.models.ai_log import AILog


async def generate_feedback(db: AsyncSession, enrollment: Enrollment) -> Feedback:
    """수강 완료 후 피드백 생성"""
    
    # 기존 피드백 확인
    from sqlalchemy import select
    existing = await db.execute(
        select(Feedback).where(Feedback.enrollment_id == enrollment.id)
    )
    feedback = existing.scalar_one_or_none()
    
    if not feedback:
        feedback = Feedback(enrollment_id=enrollment.id)
        db.add(feedback)
    
    start_time = time.time()
    
    # 수강생 피드백 생성
    student_prompt = f"""
다음 강습을 완료한 수강생의 피드백을 작성해주세요.

강습: {enrollment.lesson.title}
종목: {enrollment.lesson.sport_type.value}
수강생: {enrollment.student_name}
출석률: {enrollment.attendance_rate or 0}%

요구사항:
- 2~3문장으로 작성
- 긍정적인 톤
- 개선점도 포함
"""
    student_feedback = await generate_text(student_prompt)
    
    # 강사 피드백 생성
    instructor_prompt = f"""
다음 수강생에 대한 강사 피드백을 작성해주세요.

강습: {enrollment.lesson.title}
수강생: {enrollment.student_name}
출석률: {enrollment.attendance_rate or 0}%

요구사항:
- 2~3문장으로 작성
- 전문적인 톤
- 향후 개선 방향 제시
"""
    instructor_feedback = await generate_text(instructor_prompt)
    
    latency_ms = (time.time() - start_time) * 1000
    
    feedback.student_feedback = student_feedback
    feedback.instructor_feedback = instructor_feedback
    
    # AI 로그 저장
    ai_log = AILog(
        feature_type="feedback",
        enrollment_id=enrollment.id,
        lesson_id=enrollment.lesson_id,
        input_data={
            "student_name": enrollment.student_name,
            "lesson_title": enrollment.lesson.title,
            "attendance_rate": enrollment.attendance_rate
        },
        output_data={
            "student_feedback_length": len(student_feedback),
            "instructor_feedback_length": len(instructor_feedback)
        },
        latency_ms=latency_ms
    )
    db.add(ai_log)
    
    await db.commit()
    await db.refresh(feedback)
    
    return feedback

