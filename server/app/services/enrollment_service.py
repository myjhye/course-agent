"""
수강 신청·조회·수정·취소를 처리한다.

LLM 없이 순수 DB 쿼리만 수행하며, AI 파이프라인과 독립적으로 동작한다.
조회 함수는 강습 정보(제목·종목·썸네일)를 함께 담아 dict로 반환해
프론트가 추가 요청 없이 한 번에 쓸 수 있게 한다.

함수:
- create_enrollment()             : 수강 신청. 중복 신청이면 예외를 던진다.
- get_enrollments_by_student()    : 특정 수강생의 전체 수강 목록을 최신순으로 반환한다.
- get_all_enrollments_paginated() : 전체 수강 목록을 페이지네이션으로 반환한다.
- get_enrollment_by_id()          : 수강 ID로 단건을 조회한다.
- update_enrollment()             : 수강 상태·출석률을 수정한다.
- cancel_enrollment()             : 수강을 취소하고 DB에서 삭제한다.
- get_feedback()                  : 수강 ID로 피드백을 조회한다.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.lesson import Lesson
from app.models.feedback import Feedback
from app.schemas.enrollment import EnrollmentCreate, EnrollmentUpdate


def _get_active_thumbnail(lesson) -> Optional[str]:
    """
    강습의 활성 콘텐츠에서 썸네일 URL을 추출한다.

    콘텐츠 버전이 여러 개일 수 있어 is_active인 것만 사용한다.
    강습이 없거나 활성 콘텐츠가 없으면 None을 반환한다.
    여러 조회 함수에서 공통으로 쓰여 클래스 밖에 분리했다.
    """
    if not lesson or not lesson.contents:
        return None
    for content in lesson.contents:
        if content.is_active and content.thumbnail_url:
            return content.thumbnail_url
    return None


class EnrollmentService:

    @staticmethod
    async def create_enrollment(db: AsyncSession, data: EnrollmentCreate) -> Enrollment:
        """
        수강을 신청하고 저장한다.

        같은 수강생이 같은 강습을 중복 신청하면 ValueError를 던진다.
        중복을 허용하면 수강 이력이 꼬이고 추천·통계 데이터가 오염되기 때문이다.
        """
        # ── 1. 중복 수강 체크 ──
        # 같은 수강생·같은 강습 조합이 이미 있으면 신청을 막는다.
        existing = await db.execute(
            select(Enrollment).where(
                and_(
                    Enrollment.student_name == data.student_name,
                    Enrollment.lesson_id == data.lesson_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("DUPLICATE_ENROLLMENT")

        # ── 2. 수강 생성 ──
        enrollment = Enrollment(
            student_name=data.student_name,
            lesson_id=data.lesson_id,
            status=EnrollmentStatus.ENROLLED
        )
        db.add(enrollment)
        await db.commit()
        await db.refresh(enrollment)
        return enrollment

    @staticmethod
    async def get_enrollments_by_student(db: AsyncSession, student_name: str) -> List[dict]:
        """
        특정 수강생의 전체 수강 목록을 최신순으로 반환한다.

        강습 정보(제목·종목·난이도·썸네일)를 함께 담아 dict로 반환해
        프론트가 추가 요청 없이 수강 목록 화면을 구성할 수 있게 한다.
        """
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.student_name == student_name)
            .options(
                selectinload(Enrollment.lesson).selectinload(Lesson.contents)
            )
            # 최신 수강이 먼저 보이도록 내림차순 정렬한다.
            .order_by(desc(Enrollment.created_at))
        )
        enrollments = result.scalars().all()

        return [
            {
                "id": enrollment.id,
                "student_name": enrollment.student_name,
                "lesson_id": enrollment.lesson_id,
                "status": enrollment.status.value,
                "attendance_rate": enrollment.attendance_rate,
                "completion_date": enrollment.completion_date,
                "created_at": enrollment.created_at,
                "updated_at": enrollment.updated_at,
                "lesson_title": enrollment.lesson.title if enrollment.lesson else None,
                "lesson_sport_type": enrollment.lesson.sport_type.value if enrollment.lesson else None,
                "lesson_difficulty": enrollment.lesson.difficulty.value if enrollment.lesson else None,
                "lesson_thumbnail_url": _get_active_thumbnail(enrollment.lesson)
            }
            for enrollment in enrollments
        ]

    @staticmethod
    async def get_all_enrollments_paginated(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        lesson_id: Optional[int] = None
    ) -> dict:
        """
        전체 수강 목록을 페이지네이션으로 반환한다.

        status·lesson_id 필터를 조합할 수 있고,
        total·total_pages를 함께 반환해 프론트가 페이지 UI를 구성할 수 있게 한다.
        """
        query = select(Enrollment).options(
            selectinload(Enrollment.lesson).selectinload(Lesson.contents)
        )
        count_query = select(func.count(Enrollment.id))

        # ── 1. 필터 조건 조합 ──
        # 조건이 없으면 전체를 조회하고, 있으면 and_로 묶어 필터링한다.
        conditions = []
        if status:
            conditions.append(Enrollment.status == status)
        if lesson_id:
            conditions.append(Enrollment.lesson_id == lesson_id)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # ── 2. 전체 건수 조회 ──
        # 페이지네이션 메타(total_pages)를 계산하기 위해 필터 적용 후 전체 수를 먼저 센다.
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # ── 3. 페이지 데이터 조회 ──
        query = query.order_by(desc(Enrollment.created_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        items = list(result.scalars().all())

        items_with_lesson = []
        for enrollment in items:
            items_with_lesson.append({
                "id": enrollment.id,
                "student_name": enrollment.student_name,
                "lesson_id": enrollment.lesson_id,
                "status": enrollment.status.value,
                "attendance_rate": enrollment.attendance_rate,
                "completion_date": enrollment.completion_date,
                "created_at": enrollment.created_at,
                "updated_at": enrollment.updated_at,
                "lesson_title": enrollment.lesson.title if enrollment.lesson else None,
                "lesson_sport_type": enrollment.lesson.sport_type.value if enrollment.lesson else None,
                "lesson_difficulty": enrollment.lesson.difficulty.value if enrollment.lesson else None,
                "lesson_thumbnail_url": _get_active_thumbnail(enrollment.lesson)
            })

        return {
            "items": items_with_lesson,
            "total": total,
            "page": page,
            "page_size": page_size,
            # total_pages: 나머지가 있으면 올림해 마지막 페이지를 포함한다.
            "total_pages": (total + page_size - 1) // page_size
        }

    @staticmethod
    async def get_enrollment_by_id(db: AsyncSession, enrollment_id: int) -> Optional[Enrollment]:
        """
        수강 ID로 단건을 조회한다.

        update_enrollment·cancel_enrollment·피드백 생성에서 공통으로 먼저 호출해
        대상이 존재하는지 확인하는 용도로 쓴다.
        없으면 None을 반환한다.
        """
        result = await db.execute(
            select(Enrollment)
            .where(Enrollment.id == enrollment_id)
            .options(selectinload(Enrollment.lesson))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update_enrollment(
        db: AsyncSession,
        enrollment_id: int,
        data: EnrollmentUpdate
    ) -> Optional[dict]:
        """
        수강 상태·출석률을 수정한다.

        변경된 필드만 반영하기 위해 exclude_unset=True로 파싱해
        전달하지 않은 필드는 기존 값을 유지한다.
        수강이 없으면 None을 반환한다.
        """
        enrollment = await EnrollmentService.get_enrollment_by_id(db, enrollment_id)
        if not enrollment:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(enrollment, field, value)

        await db.commit()
        await db.refresh(enrollment)

        return {
            **enrollment.__dict__,
            "lesson_title": enrollment.lesson.title,
            "lesson_sport_type": enrollment.lesson.sport_type.value,
            "lesson_difficulty": enrollment.lesson.difficulty.value
        }

    @staticmethod
    async def cancel_enrollment(db: AsyncSession, enrollment_id: int) -> bool:
        """
        수강을 취소하고 DB에서 삭제한다.

        상태를 cancelled로 바꾸는 게 아니라 레코드 자체를 삭제한다.
        수강이 없으면 False를 반환한다.
        """
        enrollment = await EnrollmentService.get_enrollment_by_id(db, enrollment_id)
        if not enrollment:
            return False

        await db.delete(enrollment)
        await db.commit()
        return True

    @staticmethod
    async def get_feedback(db: AsyncSession, enrollment_id: int) -> Optional[Feedback]:
        """
        수강 ID로 피드백을 조회한다.

        피드백이 없으면 None을 반환한다.
        피드백 생성은 feedback_generator.py에서 담당한다.
        """
        result = await db.execute(
            select(Feedback).where(Feedback.enrollment_id == enrollment_id)
        )
        return result.scalar_one_or_none()
