from pydantic import BaseModel, EmailStr, Field, field_validator
from src.common.models.users import User
import re

PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{12,}$")


class SignupRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=30)
    phone_number: str = Field(min_length=10,max_length=10)
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str):
        if not PASSWORD_REGEX.fullmatch(v):
            raise ValueError(
                "Password must be at least 12 characters long and contain "
                "uppercase, lowercase, digit, and special character"
            )
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

