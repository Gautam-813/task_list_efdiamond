from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.security import hash_password
from app.database import get_db
from app.dependencies import redirect_if_unauthenticated
from app.main_templates import templates
from app.models.task import Task, TaskAttachment, TaskComment
from app.models.user import User
from app.services.storage import delete_attachment_file, save_task_attachment

router = APIRouter()

TASK_STATUSES = ["pending", "in_progress", "completed", "blocked"]
TASK_PRIORITIES = ["low", "medium", "high", "urgent"]
DUE_FILTERS = ["overdue", "today", "upcoming", "completed"]


def can_manage_task_details(task: Task, user: User) -> bool:
    return user.role == "admin" or task.created_by_id == user.id


def can_contribute_to_task(task: Task, user: User) -> bool:
    return can_manage_task_details(task, user) or task.assigned_to_id == user.id


def can_edit_assigned_remarks(task: Task, user: User) -> bool:
    return user.role == "admin" or task.assigned_to_id == user.id


def can_delete_attachment(attachment: TaskAttachment, user: User) -> bool:
    return (
        user.role == "admin"
        or attachment.uploaded_by_id == user.id
        or attachment.task.created_by_id == user.id
    )


def due_state(task: Task) -> str:
    today = date.today()
    if task.status == "completed":
        return "done"
    if task.deadline < today:
        return "overdue"
    if task.deadline == today:
        return "today"
    return "upcoming"


def attach_uploaded_files(
    db: Session, task: Task, current_user: User, attachments: list[UploadFile]
) -> None:
    for file in attachments:
        attachment = save_task_attachment(file, task.id, current_user)
        if attachment:
            db.add(attachment)


def parse_filter_id(value: str) -> int | None:
    if not value:
        return None
    return int(value) if value.isdigit() else None


@router.get("/")
def home():
    return RedirectResponse(url="/tasks", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/tasks")
def task_dashboard(
    request: Request,
    view: str = "all",
    status_filter: str = "",
    priority_filter: str = "",
    assignee_filter: str = "",
    creator_filter: str = "",
    due_filter: str = "",
    q: str = "",
    db: Session = Depends(get_db),
):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    query = db.query(Task).options(
        joinedload(Task.creator),
        joinedload(Task.assignee),
        joinedload(Task.attachments).joinedload(TaskAttachment.uploaded_by),
        joinedload(Task.comments).joinedload(TaskComment.user),
    )
    if view == "assigned_to_me":
        query = query.filter(Task.assigned_to_id == current_user.id)
    elif view == "created_by_me":
        query = query.filter(Task.created_by_id == current_user.id)

    if status_filter:
        query = query.filter(Task.status == status_filter)
    if priority_filter:
        query = query.filter(Task.priority == priority_filter)
    assignee_id = parse_filter_id(assignee_filter)
    creator_id = parse_filter_id(creator_filter)
    if assignee_id:
        query = query.filter(Task.assigned_to_id == assignee_id)
    if creator_id:
        query = query.filter(Task.created_by_id == creator_id)
    if due_filter:
        today = date.today()
        if due_filter == "overdue":
            query = query.filter(Task.deadline < today, Task.status != "completed")
        elif due_filter == "today":
            query = query.filter(Task.deadline == today, Task.status != "completed")
        elif due_filter == "upcoming":
            query = query.filter(Task.deadline > today, Task.status != "completed")
        elif due_filter == "completed":
            query = query.filter(Task.status == "completed")
    if q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(
            or_(Task.title.ilike(search_term), Task.description.ilike(search_term))
        )

    tasks = query.order_by(Task.deadline.asc(), Task.created_at.desc()).all()
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name.asc()).all()
    today = date.today()
    all_tasks = db.query(Task).all()
    dashboard_counts = {
        "total": len(all_tasks),
        "assigned_to_me": sum(1 for task in all_tasks if task.assigned_to_id == current_user.id),
        "overdue": sum(
            1 for task in all_tasks if task.deadline < today and task.status != "completed"
        ),
        "due_today": sum(
            1 for task in all_tasks if task.deadline == today and task.status != "completed"
        ),
        "pending": sum(1 for task in all_tasks if task.status == "pending"),
        "completed": sum(1 for task in all_tasks if task.status == "completed"),
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "current_user": current_user,
            "tasks": tasks,
            "users": users,
            "view": view,
            "status_filter": status_filter,
            "priority_filter": priority_filter,
            "assignee_filter": assignee_filter,
            "creator_filter": creator_filter,
            "due_filter": due_filter,
            "q": q.strip(),
            "statuses": TASK_STATUSES,
            "priorities": TASK_PRIORITIES,
            "due_filters": DUE_FILTERS,
            "dashboard_counts": dashboard_counts,
            "can_manage_task_details": can_manage_task_details,
            "can_contribute_to_task": can_contribute_to_task,
            "due_state": due_state,
        },
    )


@router.get("/tasks/new")
def new_task_page(request: Request, db: Session = Depends(get_db)):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name.asc()).all()
    return templates.TemplateResponse(
        "task_form.html",
        {
            "request": request,
            "current_user": current_user,
            "task": None,
            "users": users,
            "statuses": TASK_STATUSES,
            "priorities": TASK_PRIORITIES,
            "today": date.today(),
            "form_action": "/tasks/new",
            "can_manage_details": True,
            "can_edit_remarks": False,
            "can_upload_attachments": True,
        },
    )


@router.post("/tasks/new")
def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    assignment_date: date = Form(...),
    deadline: date = Form(...),
    assigned_to_id: int = Form(...),
    task_status: str = Form(...),
    priority: str = Form("medium"),
    attachments: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    if task_status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid task status")
    if priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=400, detail="Invalid task priority")

    assignee = db.query(User).filter(User.id == assigned_to_id, User.is_active.is_(True)).first()
    if not assignee:
        raise HTTPException(status_code=400, detail="Assigned user does not exist")

    task = Task(
        title=title.strip(),
        description=description.strip(),
        assignment_date=assignment_date,
        deadline=deadline,
        assigned_to_id=assigned_to_id,
        created_by_id=current_user.id,
        status=task_status,
        priority=priority,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    attach_uploaded_files(db, task, current_user, attachments)
    db.commit()
    return RedirectResponse(url="/tasks", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/tasks/{task_id}")
def task_detail_page(task_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    task = (
        db.query(Task)
        .options(
            joinedload(Task.creator),
            joinedload(Task.assignee),
            joinedload(Task.attachments).joinedload(TaskAttachment.uploaded_by),
            joinedload(Task.comments).joinedload(TaskComment.user),
        )
        .filter(Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return templates.TemplateResponse(
        "task_detail.html",
        {
            "request": request,
            "current_user": current_user,
            "task": task,
            "can_manage_details": can_manage_task_details(task, current_user),
            "can_contribute": can_contribute_to_task(task, current_user),
            "can_edit_remarks": can_edit_assigned_remarks(task, current_user),
            "can_delete_attachment": can_delete_attachment,
            "due_state": due_state(task),
        },
    )


@router.get("/tasks/{task_id}/edit")
def edit_task_page(task_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    task = (
        db.query(Task)
        .options(joinedload(Task.attachments).joinedload(TaskAttachment.uploaded_by))
        .filter(Task.id == task_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not can_contribute_to_task(task, current_user):
        raise HTTPException(status_code=403, detail="You cannot edit this task")

    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name.asc()).all()
    return templates.TemplateResponse(
        "task_form.html",
        {
            "request": request,
            "current_user": current_user,
            "task": task,
            "users": users,
            "statuses": TASK_STATUSES,
            "priorities": TASK_PRIORITIES,
            "today": date.today(),
            "form_action": f"/tasks/{task.id}/edit",
            "can_manage_details": can_manage_task_details(task, current_user),
            "can_edit_remarks": can_edit_assigned_remarks(task, current_user),
            "can_upload_attachments": can_contribute_to_task(task, current_user),
        },
    )


@router.post("/tasks/{task_id}/edit")
def update_task(
    task_id: int,
    request: Request,
    title: str | None = Form(None),
    description: str | None = Form(None),
    assignment_date: date | None = Form(None),
    deadline: date | None = Form(None),
    assigned_to_id: int | None = Form(None),
    task_status: str = Form(...),
    priority: str | None = Form(None),
    assigned_remarks: str | None = Form(None),
    attachments: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not can_contribute_to_task(task, current_user):
        raise HTTPException(status_code=403, detail="You cannot edit this task")
    if task_status not in TASK_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid task status")

    if can_manage_task_details(task, current_user):
        if not title or not assignment_date or not deadline or not assigned_to_id:
            raise HTTPException(status_code=400, detail="Missing task details")
        if not priority or priority not in TASK_PRIORITIES:
            raise HTTPException(status_code=400, detail="Invalid task priority")

        assignee = (
            db.query(User)
            .filter(User.id == assigned_to_id, User.is_active.is_(True))
            .first()
        )
        if not assignee:
            raise HTTPException(status_code=400, detail="Assigned user does not exist")

        task.title = title.strip()
        task.description = (description or "").strip()
        task.assignment_date = assignment_date
        task.deadline = deadline
        task.assigned_to_id = assigned_to_id
        task.priority = priority

    task.status = task_status
    if can_edit_assigned_remarks(task, current_user):
        task.assigned_remarks = (assigned_remarks or "").strip()
    attach_uploaded_files(db, task, current_user, attachments)
    db.commit()
    return RedirectResponse(url=f"/tasks/{task.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/tasks/{task_id}/comments")
def add_task_comment(
    task_id: int,
    request: Request,
    body: str = Form(...),
    db: Session = Depends(get_db),
):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not can_contribute_to_task(task, current_user):
        raise HTTPException(status_code=403, detail="You cannot add remarks to this task")

    comment_body = body.strip()
    if comment_body:
        db.add(TaskComment(task_id=task.id, user_id=current_user.id, body=comment_body))
        db.commit()
    return RedirectResponse(url=f"/tasks/{task.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/tasks/{task_id}/attachments")
def add_task_attachment(
    task_id: int,
    request: Request,
    attachments: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not can_contribute_to_task(task, current_user):
        raise HTTPException(status_code=403, detail="You cannot upload to this task")

    attach_uploaded_files(db, task, current_user, attachments)
    db.commit()
    return RedirectResponse(url=f"/tasks/{task.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/tasks/{task_id}/attachments/{attachment_id}/delete")
def delete_task_attachment(
    task_id: int,
    attachment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    attachment = (
        db.query(TaskAttachment)
        .options(joinedload(TaskAttachment.task))
        .filter(TaskAttachment.id == attachment_id, TaskAttachment.task_id == task_id)
        .first()
    )
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    if not can_delete_attachment(attachment, current_user):
        raise HTTPException(status_code=403, detail="You cannot delete this attachment")

    delete_attachment_file(attachment)
    db.delete(attachment)
    db.commit()
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/tasks/{task_id}/delete")
def delete_task(task_id: int, request: Request, db: Session = Depends(get_db)):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user

    task = db.query(Task).filter(Task.id == task_id).first()
    if task and not can_manage_task_details(task, current_user):
        raise HTTPException(status_code=403, detail="Only the creator or admin can delete this task")
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse(url="/tasks", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/users")
def users_page(request: Request, db: Session = Depends(get_db)):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    users = db.query(User).order_by(User.created_at.desc()).all()
    return templates.TemplateResponse(
        "admin_users.html",
        {"request": request, "current_user": current_user, "users": users, "error": None},
    )


@router.post("/admin/users")
def create_user(
    request: Request,
    username: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("user"),
    is_active: str | None = Form(None),
    db: Session = Depends(get_db),
):
    current_user = redirect_if_unauthenticated(request, db)
    if isinstance(current_user, RedirectResponse):
        return current_user
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    users = db.query(User).order_by(User.created_at.desc()).all()
    if role not in ["admin", "user"]:
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "error": "Invalid role selected.",
            },
            status_code=400,
        )

    if db.query(User).filter(User.username == username.strip()).first():
        return templates.TemplateResponse(
            "admin_users.html",
            {
                "request": request,
                "current_user": current_user,
                "users": users,
                "error": "Username already exists.",
            },
            status_code=400,
        )

    user = User(
        username=username.strip(),
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        role=role,
        is_active=is_active == "on",
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/admin/users", status_code=status.HTTP_303_SEE_OTHER)
