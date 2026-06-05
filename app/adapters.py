from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from .domain import Signature


class SignatureValidationAdapter(Protocol):
    def validate(self, citizen_name: str, dni: str, district: str) -> tuple[bool, str]:
        ...


@dataclass
class CivilRegistryValidationAdapter:
    """Adapter que normaliza una validación externa simulada del registro civil.

    En una implementación real, este adaptador conectaría con una API externa.
    Aquí valida formato básico y genera una referencia verificable.
    """

    registry_name: str = "RegistroCivil"

    def validate(self, citizen_name: str, dni: str, district: str) -> tuple[bool, str]:
        normalized = f"{citizen_name.strip().lower()}|{dni}|{district.strip().lower()}|{self.registry_name}"
        ref = sha256(normalized.encode("utf-8")).hexdigest()[:18]
        valid = len(dni) == 8 and dni.isdigit() and len(citizen_name.strip()) >= 2 and len(district.strip()) >= 2
        return valid, ref
