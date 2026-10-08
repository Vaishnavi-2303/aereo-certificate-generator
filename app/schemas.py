from datetime import date
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

class RecipientInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    course: str = Field(min_length=2, max_length=150)
    completion_date: date

    @field_validator("name", "course")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

class GenerationRequest(BaseModel):
    recipients: List[RecipientInput] = Field(min_length=1, max_length=1000)

class RecipientResult(BaseModel):
    id: int
    name: str
    status: str
    error: Optional[str] = None
    download_url: Optional[str] = None

class GenerationResponse(BaseModel):
    job_id: str
    status: str
    total: int
    successful: int
    failed: int
    recipients: List[RecipientResult]
