from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.application import AgentRun, Application
from models.user import User
from routers.deps import get_current_user

router = APIRouter()


@router.get("/")
async def list_applications(
    status: str = None,
    page: int = 1,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(Application)
        .where(Application.user_id == user.id)
        .order_by(desc(Application.created_at))
    )
    if status:
        q = q.where(Application.status == status)
    result = await db.execute(q.offset((page - 1) * limit).limit(limit))
    return result.scalars().all()


@router.get("/runs")
async def list_runs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRun).where(AgentRun.user_id == user.id)
        .order_by(desc(AgentRun.started_at)).limit(20)
    )
    return result.scalars().all()


@router.get("/runs/active")
async def active_run(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentRun)
        .where(AgentRun.user_id == user.id, AgentRun.status == "running")
        .order_by(desc(AgentRun.started_at))
    )
    return result.scalar_one_or_none()


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == run_id, AgentRun.user_id == user.id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/run")
async def trigger_run(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    active = await db.execute(
        select(AgentRun).where(AgentRun.user_id == user.id, AgentRun.status == "running")
    )
    if active.scalar_one_or_none():
        raise HTTPException(400, "An agent run is already in progress")

    from agent.orchestrator import run_agent_for_user
    background_tasks.add_task(run_agent_for_user, str(user.id))
    return {"message": "Agent run started"}
