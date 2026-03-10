from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from database import get_db
from models.user import User
from models.application import Application, AgentRun
from routers.deps import get_current_user
from agent.orchestrator import run_agent_for_user

router = APIRouter()

@router.get("/")
async def get_applications(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Application).where(Application.user_id == user.id).order_by(desc(Application.created_at))
    if status:
        query = query.where(Application.status == status)
    
    # Simple pagination
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

@router.get("/runs")
async def get_runs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.user_id == user.id)
        .order_by(desc(AgentRun.started_at))
        .limit(10)
    )
    return result.scalars().all()

@router.get("/runs/{run_id}")
async def get_run_detail(
    run_id: str, 
    user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@router.post("/run")
async def trigger_run(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if a run is already active
    active_result = await db.execute(
        select(AgentRun).where(AgentRun.user_id == user.id, AgentRun.status == "running")
    )
    if active_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An agent run is already in progress.")

    background_tasks.add_task(run_agent_for_user, str(user.id))
    return {"message": "Agent run initiated in the background."}

@router.get("/runs/active")
async def get_active_run(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.user_id == user.id, AgentRun.status == "running")
        .order_by(desc(AgentRun.started_at))
    )
    return result.scalar_one_or_none()
