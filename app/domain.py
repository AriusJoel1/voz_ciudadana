from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
import json


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class Comment:
    id: str
    author: str
    body: str
    created_at: datetime


@dataclass
class Modification:
    id: str
    author: str
    body: str
    created_at: datetime


@dataclass
class Resource:
    id: str
    name: str
    kind: str
    url: str
    checksum: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Signature:
    id: str
    citizen_name: str
    dni: str
    district: str
    valid: bool
    provider_reference: str
    created_at: datetime


@dataclass
class Initiative:
    id: str
    title: str
    summary: str
    collective: str
    subject: str
    created_at: datetime
    deadline_at: datetime
    signatures: List[Signature] = field(default_factory=list)
    comments: List[Comment] = field(default_factory=list)
    modifications: List[Modification] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    frozen: bool = False
    frozen_at: Optional[datetime] = None
    frozen_hash: Optional[str] = None
    submitted_at: Optional[datetime] = None
    congress_ref: Optional[str] = None
    committees: List[str] = field(default_factory=list)
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def signature_count(self) -> int:
        return sum(1 for s in self.signatures if s.valid)

    @property
    def is_expired(self) -> bool:
        return utcnow() > self.deadline_at

    @property
    def status(self) -> str:
        if self.submitted_at:
            return "ENVIADA"
        if self.frozen:
            return "CONGELADA"
        if self.is_expired:
            return "VENCIDA"
        return "ABIERTA"

    def snapshot(self) -> Dict[str, Any]:
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if hasattr(obj, "__dict__"):
                return asdict(obj)
            if isinstance(obj, list):
                return [serialize(x) for x in obj]
            if isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            return obj

        return serialize(asdict(self))

    def to_dict(self) -> Dict[str, Any]:
        return self.snapshot()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Initiative":
        def dt(v):
            return datetime.fromisoformat(v) if isinstance(v, str) else v

        obj = cls(
            id=data["id"],
            title=data["title"],
            summary=data["summary"],
            collective=data["collective"],
            subject=data["subject"],
            created_at=dt(data["created_at"]),
            deadline_at=dt(data["deadline_at"]),
            frozen=data.get("frozen", False),
            frozen_at=dt(data["frozen_at"]) if data.get("frozen_at") else None,
            frozen_hash=data.get("frozen_hash"),
            submitted_at=dt(data["submitted_at"]) if data.get("submitted_at") else None,
            congress_ref=data.get("congress_ref"),
            committees=data.get("committees", []),
            audit_log=data.get("audit_log", []),
        )
        obj.signatures = [
            Signature(
                id=s["id"],
                citizen_name=s["citizen_name"],
                dni=s["dni"],
                district=s.get("district", ""),
                valid=s.get("valid", False),
                provider_reference=s.get("provider_reference", ""),
                created_at=dt(s["created_at"]),
            )
            for s in data.get("signatures", [])
        ]
        obj.comments = [
            Comment(id=c["id"], author=c["author"], body=c["body"], created_at=dt(c["created_at"]))
            for c in data.get("comments", [])
        ]
        obj.modifications = [
            Modification(id=m["id"], author=m["author"], body=m["body"], created_at=dt(m["created_at"]))
            for m in data.get("modifications", [])
        ]
        obj.resources = [
            Resource(
                id=r["id"],
                name=r["name"],
                kind=r["kind"],
                url=r["url"],
                checksum=r["checksum"],
                metadata=r.get("metadata", {}),
            )
            for r in data.get("resources", [])
        ]
        return obj
