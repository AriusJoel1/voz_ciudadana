from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Dict, Any


@dataclass
class ResourceArtifact:
    name: str
    kind: str
    url: str
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "url": self.url,
            "notes": self.notes,
            "metadata": dict(self.metadata),
        }


class ResourceDecorator:
    def __init__(self, wrapped: ResourceArtifact):
        self._wrapped = wrapped

    def to_dict(self) -> Dict[str, Any]:
        return self._wrapped.to_dict()


class ChecksumDecorator(ResourceDecorator):
    def to_dict(self) -> Dict[str, Any]:
        payload = self._wrapped.to_dict()
        raw = f"{payload['name']}|{payload['kind']}|{payload['url']}|{payload.get('notes','')}"
        payload["metadata"]["checksum"] = sha256(raw.encode("utf-8" )).hexdigest()
        payload["metadata"]["decorator"] = "checksum"
        return payload


class EvidenceMetadataDecorator(ResourceDecorator):
    def __init__(self, wrapped: ResourceArtifact, source: str):
        super().__init__(wrapped)
        self._source = source

    def to_dict(self) -> Dict[str, Any]:
        payload = self._wrapped.to_dict()
        payload["metadata"]["source"] = self._source
        payload["metadata"]["decorator"] = payload["metadata"].get("decorator", "") + "+evidence"
        return payload
