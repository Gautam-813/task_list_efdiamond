import re

from pydantic import BaseModel, Field, field_validator


PHONE_REGEX = re.compile(r"^\+[1-9]\d{1,14}$")


class UserForm(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    role: str = "user"
    is_active: bool = True
    phone_number: str = ""

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if v and not PHONE_REGEX.match(v):
            raise ValueError(
                "Phone number must be in E.164 format (e.g., +919876543210)"
            )
        return v

