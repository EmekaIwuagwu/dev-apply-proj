from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from database import get_db
from models.user import User, JobPreference
from schemas.user import UserResponse, JobPreferenceResponse, JobPreferenceUpdate
from routers.deps import get_current_user
import base64

router = APIRouter()

@router.get("/profile", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return user

@router.get("/preferences", response_model=JobPreferenceResponse)
async def get_preferences(user: User = Depends(get_current_user)):
    return user.job_preferences

@router.put("/preferences", response_model=JobPreferenceResponse)
async def update_preferences(
    prefs_in: JobPreferenceUpdate, 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    prefs = user.job_preferences
    for field, value in prefs_in.dict().items():
        setattr(prefs, field, value)
    await db.commit()
    await db.refresh(prefs)
    return prefs

@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...), 
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    encoded = base64.b64encode(content).decode("utf-8")
    # Update user logic here
    return {"filename": file.filename, "message": "Resume uploaded successfully"}

@router.patch("/agent/toggle")
async def toggle_agent(enabled: bool, db: AsyncSession = Depends(get_db)):
    # Update user.agent_enabled logic here
    return {"agent_enabled": enabled}
