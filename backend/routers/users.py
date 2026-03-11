import base64

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.user import JobPreference, User
from routers.deps import get_current_user
from schemas.user import JobPreferenceResponse, JobPreferenceUpdate, UserResponse

router = APIRouter()


@router.get("/profile", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return user


@router.get("/preferences", response_model=JobPreferenceResponse)
async def get_preferences(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobPreference).where(JobPreference.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        raise HTTPException(status_code=404, detail="Preferences not found")
    return prefs


@router.put("/preferences", response_model=JobPreferenceResponse)
async def update_preferences(
    body: JobPreferenceUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(JobPreference).where(JobPreference.user_id == user.id))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = JobPreference(user_id=user.id, job_titles=[], skills=[])
        db.add(prefs)
    for field, value in body.dict(exclude_unset=True).items():
        setattr(prefs, field, value)
    await db.commit()
    await db.refresh(prefs)
    return prefs


@router.post("/resume")
async def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    user.resume_base64 = base64.b64encode(content).decode()
    user.resume_filename = file.filename
    await db.commit()
    return {"filename": file.filename, "message": "Resume uploaded"}


@router.patch("/agent/toggle")
async def toggle_agent(
    enabled: bool,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user.agent_enabled = enabled
    await db.commit()
    return {"agent_enabled": enabled}
