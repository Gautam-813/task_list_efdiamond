from pathlib import Path
from uuid import uuid4
import os
import shutil

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

# Ensure local upload directory exists
LOCAL_UPLOAD_DIR = Path("/opt/task_list_app/uploads")
LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret,
    secure=True,
)


def _validate_upload(file: UploadFile) -> int:
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

    # Calculate file size in bytes
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    
    # Let's assume a hard cap, maybe 500MB? The current settings.max_upload_size_mb is 10.
    # We need to increase that to at least 100.
    max_bytes = 500 * 1024 * 1024 
    if size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size of 500 MB.",
        )
    return size


def _save_locally(file: UploadFile, filename: str) -> str:
    stored_filename = f"{uuid4().hex}_{filename}"
    file_path = LOCAL_UPLOAD_DIR / stored_filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return str(file_path)


def save_task_attachment(file: UploadFile, task_id: int, uploader: User) -> TaskAttachment | None:
    if not file.filename:
        return None

    size = _validate_upload(file)
    original_filename = Path(file.filename).name
    
    # Hybrid Logic: Threshold 100MB
    threshold = 100 * 1024 * 1024
    
    attachment_data = {
        "task_id": task_id,
        "uploaded_by_id": uploader.id,
        "original_filename": original_filename,
        "content_type": file.content_type or "application/octet-stream",
    }

    if size >= threshold:
        # Save Local
        file_path = _save_locally(file, original_filename)
        return TaskAttachment(
            **attachment_data,
            stored_filename="LOCAL",
            file_path=file_path,
        )
    else:
        # Try Cloudinary
        public_id = f"task_{task_id}/{uuid4().hex}"
        try:
            result = cloudinary.uploader.upload(
                file.file,
                public_id=public_id,
                resource_type="auto",
            )
            return TaskAttachment(
                **attachment_data,
                stored_filename=public_id,
                file_path=result["secure_url"],
            )
        except Exception:
            # Fallback to local
            file_path = _save_locally(file, original_filename)
            return TaskAttachment(
                **attachment_data,
                stored_filename="LOCAL",
                file_path=file_path,
            )


def delete_attachment_file(attachment: TaskAttachment) -> None:
    if not attachment.stored_filename:
        return
        
    if attachment.stored_filename == "LOCAL":
        if os.path.exists(attachment.file_path):
            os.remove(attachment.file_path)
    else:
        for resource_type in ("image", "raw", "video"):
            try:
                cloudinary.uploader.destroy(attachment.stored_filename, resource_type=resource_type)
                return
            except Exception:
                pass
