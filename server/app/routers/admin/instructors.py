from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.database import get_db
from app.schemas.instructor import InstructorCreate, InstructorResponse
from app.services.instructor_service import InstructorService

router = APIRouter(prefix="/api/admin/instructors", tags=["admin-instructors"])


@router.post("/", response_model=InstructorResponse, status_code=201)
async def create_instructor(data: InstructorCreate, db: AsyncSession = Depends(get_db)):
    """강사 등록"""
    return await InstructorService.create_instructor(db, data)


@router.get("/", response_model=List[InstructorResponse])
async def get_instructors(db: AsyncSession = Depends(get_db)):
    """강사 목록"""
    return await InstructorService.get_instructors(db)


@router.get("/{instructor_id}", response_model=InstructorResponse)
async def get_instructor(instructor_id: int, db: AsyncSession = Depends(get_db)):
    """강사 상세"""
    instructor = await InstructorService.get_instructor_by_id(db, instructor_id)
    if not instructor:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return instructor


@router.delete("/{instructor_id}")
async def delete_instructor(instructor_id: int, db: AsyncSession = Depends(get_db)):
    """강사 삭제"""
    success = await InstructorService.delete_instructor(db, instructor_id)
    if not success:
        raise HTTPException(status_code=404, detail="Instructor not found")
    return {"message": "Instructor deleted"}

