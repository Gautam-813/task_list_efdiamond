from datetime import date

from pydantic import BaseModel, Field


class TaskForm(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = ""
    assignment_date: date
    deadline: date
    assigned_to_id: int
    status: str

