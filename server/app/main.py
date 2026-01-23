from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# 운영자 라우터
from app.routers.admin.instructors import router as admin_instructors_router
from app.routers.admin.lessons import router as admin_lessons_router
from app.routers.admin.enrollments import router as admin_enrollments_router

# 공개/수강생 라우터
from app.routers.lessons import router as lessons_router
from app.routers.my.enrollments import router as my_enrollments_router

# 채팅
from app.routers.chat import router as chat_router

from app.config import settings
from app.database import engine, Base
from app.models import Instructor, Lesson, LessonContent, Enrollment, Feedback, AILog, Chat, FAQ  # 모델 import 필수


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작할 때 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # 종료할 때 정리 (필요하면)


app = FastAPI(
    title="Course Agent API",
    description="LLM 기반 강의 플랫폼 API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(admin_instructors_router)
app.include_router(admin_lessons_router)
app.include_router(admin_enrollments_router)
app.include_router(lessons_router)
app.include_router(my_enrollments_router)
app.include_router(chat_router)

# 정적 파일 서빙 (썸네일 이미지)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

