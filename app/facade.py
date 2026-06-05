from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from typing import List, Optional

from .adapters import SignatureValidationAdapter, CivilRegistryValidationAdapter
from .decorators import ResourceArtifact, ChecksumDecorator, EvidenceMetadataDecorator
from .domain import Initiative, Signature, Comment, Modification, Resource, new_id, utcnow
from .repository import InitiativeRepository


class FreezeService:
    def freeze(self, initiative: Initiative) -> str:
        snapshot = initiative.snapshot()
        canonical = str(snapshot).encode("utf-8")
        return sha256(canonical).hexdigest()


class CryptographicFreezeProxy:
    def __init__(self, freeze_service: FreezeService, threshold: int, max_days: int):
        self._freeze_service = freeze_service
        self.threshold = threshold
        self.max_days = max_days

    def freeze(self, initiative: Initiative) -> str:
        if initiative.frozen:
            return initiative.frozen_hash or ""
        if initiative.signature_count < self.threshold:
            raise ValueError(f"Se requieren al menos {self.threshold} firmas válidas para congelar la iniciativa.")
        if utcnow() > initiative.deadline_at:
            raise ValueError("La iniciativa venció y no puede congelarse.")
        freeze_hash = self._freeze_service.freeze(initiative)
        initiative.frozen = True
        initiative.frozen_at = utcnow()
        initiative.frozen_hash = freeze_hash
        initiative.audit_log.append({"event": "freeze", "at": utcnow().isoformat(), "hash": freeze_hash})
        return freeze_hash


@dataclass
class CommitteeRouter:
    mapping: dict

    def route(self, subject: str) -> List[str]:
        s = subject.lower()
        for keyword, committees in self.mapping.items():
            if keyword in s:
                return committees
        return ["Comisión de Constitución", "Comisión de Justicia"]


class LegislativeInitiativeFacade:
    def __init__(
        self,
        repository: InitiativeRepository,
        signature_adapter: SignatureValidationAdapter | None = None,
        freeze_proxy: CryptographicFreezeProxy | None = None,
        committee_router: CommitteeRouter | None = None,
        threshold: int = 25000,
        max_days: int = 90,
    ):
        self.repository = repository
        self.signature_adapter = signature_adapter or CivilRegistryValidationAdapter()
        self.freeze_proxy = freeze_proxy or CryptographicFreezeProxy(FreezeService(), threshold, max_days)
        self.committee_router = committee_router or CommitteeRouter(
            mapping={
                "salud": ["Comisión de Salud"],
                "educ": ["Comisión de Educación"],
                "trab": ["Comisión de Trabajo"],
                "ambiente": ["Comisión de Ambiente"],
                "seguridad": ["Comisión de Seguridad Ciudadana"],
            }
        )
        self.threshold = threshold
        self.max_days = max_days

    def create_initiative(self, title: str, summary: str, collective: str, subject: str, deadline_days: int = 90) -> Initiative:
        deadline_days = min(max(deadline_days, 1), self.max_days)
        initiative = Initiative(
            id=new_id("ini"),
            title=title.strip(),
            summary=summary.strip(),
            collective=collective.strip(),
            subject=subject.strip(),
            created_at=utcnow(),
            deadline_at=utcnow() + timedelta(days=deadline_days),
        )
        initiative.audit_log.append({"event": "create", "at": utcnow().isoformat()})
        self.repository.save(initiative)
        return initiative

    def get(self, initiative_id: str) -> Initiative:
        initiative = self.repository.get(initiative_id)
        if not initiative:
            raise KeyError("Iniciativa no encontrada")
        return initiative

    def list(self) -> List[Initiative]:
        return sorted(self.repository.list(), key=lambda i: i.created_at, reverse=True)

    def _ensure_editable(self, initiative: Initiative) -> None:
        if initiative.frozen:
            raise ValueError("La iniciativa está congelada criptográficamente y ya no acepta cambios.")
        if initiative.is_expired:
            raise ValueError("La iniciativa ya venció y no acepta cambios.")

    def add_comment(self, initiative_id: str, author: str, body: str) -> Initiative:
        initiative = self.get(initiative_id)
        self._ensure_editable(initiative)
        initiative.comments.append(Comment(id=new_id("c"), author=author.strip(), body=body.strip(), created_at=utcnow()))
        initiative.audit_log.append({"event": "comment", "author": author, "at": utcnow().isoformat()})
        return self.repository.save(initiative)

    def add_modification(self, initiative_id: str, author: str, body: str) -> Initiative:
        initiative = self.get(initiative_id)
        self._ensure_editable(initiative)
        initiative.modifications.append(Modification(id=new_id("m"), author=author.strip(), body=body.strip(), created_at=utcnow()))
        initiative.audit_log.append({"event": "modification", "author": author, "at": utcnow().isoformat()})
        return self.repository.save(initiative)

    def add_resource(self, initiative_id: str, name: str, kind: str, url: str, notes: str = "") -> Initiative:
        initiative = self.get(initiative_id)
        self._ensure_editable(initiative)
        artifact = ResourceArtifact(name=name.strip(), kind=kind.strip(), url=url.strip(), notes=notes.strip())
        artifact = EvidenceMetadataDecorator(artifact, source=initiative.collective)
        artifact = ChecksumDecorator(artifact)  # type: ignore[arg-type]
        data = artifact.to_dict()
        res = Resource(
            id=new_id("r"),
            name=data["name"],
            kind=data["kind"],
            url=data["url"],
            checksum=data["metadata"]["checksum"],
            metadata=data["metadata"],
        )
        initiative.resources.append(res)
        initiative.audit_log.append({"event": "resource", "name": name, "at": utcnow().isoformat()})
        return self.repository.save(initiative)

    def add_signature(self, initiative_id: str, citizen_name: str, dni: str, district: str) -> Initiative:
        initiative = self.get(initiative_id)
        self._ensure_editable(initiative)
        already = any(sig.dni == dni for sig in initiative.signatures)
        if already:
            raise ValueError("Este DNI ya registró una firma para esta iniciativa.")
        valid, reference = self.signature_adapter.validate(citizen_name, dni, district)
        signature = Signature(
            id=new_id("s"),
            citizen_name=citizen_name.strip(),
            dni=dni,
            district=district.strip(),
            valid=valid,
            provider_reference=reference,
            created_at=utcnow(),
        )
        initiative.signatures.append(signature)
        initiative.audit_log.append({"event": "signature", "dni": dni, "valid": valid, "at": utcnow().isoformat()})
        if initiative.signature_count >= self.threshold and not initiative.frozen:
            self.freeze_proxy.freeze(initiative)
        return self.repository.save(initiative)

    def freeze(self, initiative_id: str) -> Initiative:
        initiative = self.get(initiative_id)
        freeze_hash = self.freeze_proxy.freeze(initiative)
        initiative.audit_log.append({"event": "manual_freeze", "hash": freeze_hash, "at": utcnow().isoformat()})
        return self.repository.save(initiative)

    def submit_to_congress(self, initiative_id: str) -> Initiative:
        initiative = self.get(initiative_id)
        if not initiative.frozen:
            raise ValueError("Primero debe congelarse criptográficamente la iniciativa.")
        if initiative.signature_count < self.threshold:
            raise ValueError(f"Se requieren al menos {self.threshold} firmas válidas para enviar al Congreso.")
        if initiative.submitted_at:
            return initiative
        initiative.submitted_at = utcnow()
        initiative.congress_ref = f"CG-{initiative.id.upper()}"
        initiative.committees = self.committee_router.route(initiative.subject)
        initiative.audit_log.append({"event": "submit", "ref": initiative.congress_ref, "at": utcnow().isoformat()})
        return self.repository.save(initiative)
