"""Flow routes — Task management with AI-powered summaries and status tracking."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Task, TaskStatus, TaskPriority, TaskSource, User
from app.api.deps import get_org_context, OrgContext
from app.api.schemas import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()


def _task_to_response(t: Task) -> TaskResponse:
    return TaskResponse(
        id=t.id,
        title=t.title,
        description=t.description,
        status=t.status.value if isinstance(t.status, TaskStatus) else t.status,
        priority=t.priority.value if isinstance(t.priority, TaskPriority) else t.priority,
        assignee_id=t.assignee_id,
        source=t.source.value if isinstance(t.source, TaskSource) else t.source,
        source_url=t.source_url,
        source_id=t.source_id,
        ai_summary=t.ai_summary,
        blockers=t.blockers or [],
        labels=t.labels or [],
        due_date=t.due_date,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.get("/tasks", response_model=list[TaskResponse])
async def list_tasks(
    status: str | None = Query(None),
    priority: str | None = Query(None),
    assignee_id: uuid.UUID | None = Query(None),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[TaskResponse]:
    query = select(Task).where(Task.org_id == ctx.org_id)

    if status:
        query = query.where(Task.status == TaskStatus(status))
    if priority:
        query = query.where(Task.priority == TaskPriority(priority))
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)

    query = query.order_by(Task.updated_at.desc()).limit(100)
    result = await db.execute(query)
    return [_task_to_response(t) for t in result.scalars().all()]


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(
    req: TaskCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    task = Task(
        org_id=ctx.org_id,
        title=req.title,
        description=req.description,
        status=TaskStatus(req.status),
        priority=TaskPriority(req.priority),
        assignee_id=req.assignee_id,
        source=TaskSource(req.source),
        source_url=req.source_url,
        source_id=req.source_id,
        ai_summary=req.ai_summary,
        blockers=req.blockers,
        labels=req.labels,
        due_date=req.due_date,
    )
    db.add(task)
    await db.flush()
    return _task_to_response(task)


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.org_id == ctx.org_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    req: TaskUpdate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.org_id == ctx.org_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    updates = req.model_dump(exclude_unset=True)
    if "status" in updates:
        updates["status"] = TaskStatus(updates["status"])
    if "priority" in updates:
        updates["priority"] = TaskPriority(updates["priority"])

    for key, value in updates.items():
        setattr(task, key, value)

    await db.flush()
    return _task_to_response(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(
    task_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> None:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.org_id == ctx.org_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)


@router.get("/tasks/stats/summary")
async def task_stats(
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Task.status, func.count(Task.id))
        .where(Task.org_id == ctx.org_id)
        .group_by(Task.status)
    )
    counts = {row[0].value if isinstance(row[0], TaskStatus) else row[0]: row[1] for row in result.all()}
    return {
        "todo": counts.get("todo", 0),
        "in_progress": counts.get("in_progress", 0),
        "in_review": counts.get("in_review", 0),
        "done": counts.get("done", 0),
        "total": sum(counts.values()),
    }
