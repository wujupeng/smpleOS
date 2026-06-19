from fastapi import APIRouter
from pydantic import BaseModel

from src.domain.services.human_task_service import HumanTaskService
from src.infrastructure.database import get_pg_pool

router = APIRouter()


class ApproveRequest(BaseModel):
    comments: str = ""


class RejectRequest(BaseModel):
    comments: str = ""


class DecideRequest(BaseModel):
    decision: str
    comments: str = ""


@router.get("/human-tasks")
async def list_pending_tasks(assignee: str | None = None):
    pool = await get_pg_pool()
    tasks = await HumanTaskService.list_pending_tasks(assignee=assignee, pool=pool)
    return {"tasks": tasks}


@router.post("/human-tasks/{task_id}/approve")
async def approve_task(task_id: str, req: ApproveRequest):
    pool = await get_pg_pool()
    return await HumanTaskService.approve_task(task_id, comments=req.comments, pool=pool)


@router.post("/human-tasks/{task_id}/reject")
async def reject_task(task_id: str, req: RejectRequest):
    pool = await get_pg_pool()
    return await HumanTaskService.reject_task(task_id, comments=req.comments, pool=pool)


@router.post("/human-tasks/{task_id}/decide")
async def decide_task(task_id: str, req: DecideRequest):
    pool = await get_pg_pool()
    return await HumanTaskService.decide_task(task_id, decision=req.decision, comments=req.comments, pool=pool)