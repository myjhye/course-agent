from fastapi import HTTPException


class CourseNotFoundError(HTTPException):
    def __init__(self, course_id: int):
        super().__init__(status_code=404, detail=f"Course with id {course_id} not found")

