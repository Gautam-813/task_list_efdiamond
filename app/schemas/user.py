from pydantic import BaseModel, Field


class UserForm(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    role: str = "user"
    is_active: bool = True

