from pathlib import Path
from uuid import uuid4

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.models.task import TaskAttachment
from app.models.user import User

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

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


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

    original_filename = Path(file.filename).name
    suffix = Path(original_filename).suffix
    public_id = f"task_{task_id}/{uuid4().hex}"

    result = cloudinary.uploader.upload(
        file.file,
        public_id=public_id,
        resource_type="auto",
    )

    return TaskAttachment(
        task_id=task_id,
        uploaded_by_id=uploader.id,
        original_filename=original_filename,
        stored_filename=public_id,
        file_path=result["secure_url"],
        content_type=file.content_type or result.get("resource_type", "application/octet-stream"),
    )


def delete_attachment_file(attachment: TaskAttachment) -> None:
    if not attachment.stored_filename:
        return
    for resource_type in ("image", "raw", "video"):
        try:
            cloudinary.uploader.destroy(attachment.stored_filename, resource_type=resource_type)
            return
        except Exception:
            pass
