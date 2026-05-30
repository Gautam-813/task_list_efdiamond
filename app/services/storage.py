from pathlib import Path
from shutil import rmtree
from uuid import uuid4

from fastapi import UploadFile

from app.models.task import TaskAttachment
from app.models.user import User


UPLOAD_ROOT = Path("app/uploads")


def save_task_attachment(file: UploadFile, task_id: int, uploader: User) -> TaskAttachment | None:
    if not file.filename:
        return None

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
