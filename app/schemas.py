from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class InitiativeCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    summary: str = Field(min_length=10, max_length=4000)
    collective: str = Field(min_length=3, max_length=180)
    subject: str = Field(min_length=3, max_length=180)
    deadline_days: int = Field(default=90, ge=1, le=90)


class CommentCreate(BaseModel):
    author: str = Field(min_length=2, max_length=120)
    body: str = Field(min_length=1, max_length=4000)


class ModificationCreate(BaseModel):
    author: str = Field(min_length=2, max_length=120)
    body: str = Field(min_length=1, max_length=4000)


class ResourceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    kind: str = Field(min_length=2, max_length=40)
    url: str = Field(min_length=5, max_length=1000)
    notes: str = Field(default="", max_length=2000)


class SignatureCreate(BaseModel):
    citizen_name: str = Field(min_length=2, max_length=120)
    dni: str = Field(min_length=8, max_length=8)
    district: str = Field(min_length=2, max_length=120)

    @field_validator("dni")
    @classmethod
    def dni_must_be_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("El DNI debe contener solo números")
        return v


class InitiativeResponse(BaseModel):
    id: str
    title: str
    summary: str
    collective: str
    subject: str
    created_at: datetime
    deadline_at: datetime
    signature_count: int
    signatures_total: int
    frozen: bool
    frozen_at: Optional[datetime]
    frozen_hash: Optional[str]
    submitted_at: Optional[datetime]
    congress_ref: Optional[str]
    committees: List[str]
    status: str
    comments_count: int
    modifications_count: int
    resources_count: int


class MessageResponse(BaseModel):
    message: str
    initiative_id: Optional[str] = None
    frozen_hash: Optional[str] = None
    status: Optional[str] = None
