from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.task import TaskAttachment
from app.models.user import User


UPLOAD_ROOT = Path("app/uploads")

ALLOWED_CONTENT_TYPES: set[str] = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/zip",
    "application/gzip",
    "application/json",
    "application/xml",
}

BLOCKED_EXTENSIONS: set[str] = {
    ".exe", ".bat", ".cmd", ".com", ".msi", ".scr", ".ps1", ".sh",
    ".vbs", ".jse", ".wsf", ".js", ".jar", ".php", ".asp", ".aspx",
    ".cgi", ".pl", ".py", ".rb",
}


def _validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File has no name.")

    ext = Path(file.filename).suffix.lower()
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"File type '{ext}' is not allowed.")

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type '{file.content_type}' is not allowed. Allowed: {allowed}",
        )

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB.",
        )


def save_task_attachment(file: UploadFile, task_id: int, uploader: User) -> TaskAttachment | None:
    if not file.filename:
        return None

    _validate_upload(file)

    task_dir = UPLOAD_ROOT / str(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)

    original_filename = Path(file.filename).name
    suffix = Path(original_filename).suffix
    stored_filename = f"{uuid4().hex}{suffix}"
    target = task_dir / stored_filename

    with target.open("wb") as buffer:
        while chunk := file.file.read(1024 * 1024):
            buffer.write(chunk)

    return TaskAttachment(
        task_id=task_id,
        uploaded_by_id=uploader.id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(target.as_posix()),
        content_type=file.content_type or "application/octet-stream",
    )


def delete_attachment_file(attachment: TaskAttachment) -> None:
    path = Path(attachment.file_path)
    if path.exists() and path.is_file():
        path.unlink()

    parent = path.parent
    if parent.exists() and parent != UPLOAD_ROOT and not any(parent.iterdir()):
        rmtree(parent)
