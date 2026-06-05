from datetime import datetime, timedelta, timezone

from app.adapters import CivilRegistryValidationAdapter
from app.facade import LegislativeInitiativeFacade, CryptographicFreezeProxy, FreezeService, CommitteeRouter
from app.repository import JsonFileInitiativeRepository


def make_facade(tmp_path, threshold=3, max_days=90):
    repo = JsonFileInitiativeRepository(tmp_path / 'initiatives.json')
    facade = LegislativeInitiativeFacade(
        repository=repo,
        signature_adapter=CivilRegistryValidationAdapter(),
        freeze_proxy=CryptographicFreezeProxy(FreezeService(), threshold=threshold, max_days=max_days),
        committee_router=CommitteeRouter(mapping={'salud': ['Comisión de Salud']}),
        threshold=threshold,
        max_days=max_days,
    )
    return facade


def test_create_and_add_signature(tmp_path):
    facade = make_facade(tmp_path)
    ini = facade.create_initiative('Ley de Salud', 'Propuesta de reforma sanitaria', 'Colectivo Saludable', 'salud pública')
    ini = facade.add_signature(ini.id, 'Ana Pérez', '12345678', 'Lima')
    assert ini.signature_count == 1
    assert ini.signatures[0].valid is True


def test_duplicate_signature_is_rejected(tmp_path):
    facade = make_facade(tmp_path)
    ini = facade.create_initiative('Ley de Salud', 'Propuesta de reforma sanitaria', 'Colectivo Saludable', 'salud pública')
    facade.add_signature(ini.id, 'Ana Pérez', '12345678', 'Lima')
    try:
        facade.add_signature(ini.id, 'Ana Pérez', '12345678', 'Lima')
        assert False, 'Debe rechazar el DNI repetido'
    except ValueError as exc:
        assert 'ya registró una firma' in str(exc)


def test_freeze_requires_threshold(tmp_path):
    facade = make_facade(tmp_path, threshold=2)
    ini = facade.create_initiative('Ley de Ambiente', 'Propuesta ambiental', 'Colectivo Verde', 'ambiente')
    facade.add_signature(ini.id, 'Ana Pérez', '12345678', 'Lima')
    try:
        facade.freeze(ini.id)
        assert False, 'No debe congelar sin suficientes firmas'
    except ValueError as exc:
        assert 'al menos 2 firmas' in str(exc)


def test_freeze_and_submit(tmp_path):
    facade = make_facade(tmp_path, threshold=2)
    ini = facade.create_initiative('Ley de Salud', 'Propuesta sanitaria', 'Colectivo Saludable', 'salud pública')
    facade.add_signature(ini.id, 'Ana Pérez', '12345678', 'Lima')
    facade.add_signature(ini.id, 'Luis Rojas', '87654321', 'Callao')
    ini = facade.get(ini.id)
    assert ini.frozen is True
    assert ini.frozen_hash
    ini = facade.submit_to_congress(ini.id)
    assert ini.submitted_at is not None
    assert ini.committees == ['Comisión de Salud']


def test_expired_initiative_cannot_accept_changes(tmp_path):
    facade = make_facade(tmp_path)
    ini = facade.create_initiative('Ley de Educación', 'Propuesta educativa', 'Colectivo Educar', 'educación')
    expired = facade.get(ini.id)
    expired.deadline_at = datetime.now(timezone.utc) - timedelta(days=1)
    facade.repository.save(expired)
    try:
        facade.add_comment(ini.id, 'Marta', 'Comentario')
        assert False, 'No debe aceptar cambios vencida'
    except ValueError as exc:
        assert 'venció' in str(exc)
