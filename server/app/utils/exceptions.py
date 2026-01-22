from fastapi import HTTPException, status


class CourseNotFoundError(HTTPException):
    def __init__(self, course_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Course {course_id} not found"
        )


class EnrollmentNotFoundError(HTTPException):
    def __init__(self, enrollment_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Enrollment {enrollment_id} not found"
        )


class AlreadyEnrolledError(HTTPException):
    def __init__(self, course_id: int):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Already enrolled in course {course_id}"
        )

