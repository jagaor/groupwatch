import pytest
from src.state_store import StateStore


def _miembro(cn: str, sam: str) -> dict:
    # Construye un miembro normalizado tal y como lo produce GroupParser
    return {
        "cn": cn,
        "dn": f"CN={cn},OU=Grupos,DC=corp,DC=local",
        "samaccountname": sam,
        "timestamp": "2024-01-01T00:00:00Z",
    }


def test_save_and_load_state(tmp_path):
    store = StateStore(db_path=str(tmp_path / "groupwatch.db"))
    miembros = [_miembro("jperez", "jperez"), _miembro("mgarcia", "mgarcia")]
    store.save_state("Domain Admins", miembros)
    recuperado = store.load_state("Domain Admins")
    assert recuperado is not None
    assert len(recuperado) == 2
    sams = sorted(m["samaccountname"] for m in recuperado)
    assert sams == ["jperez", "mgarcia"]


def test_load_nonexistent_returns_none(tmp_path):
    store = StateStore(db_path=str(tmp_path / "groupwatch.db"))
    assert store.load_state("Enterprise Admins") is None


def test_save_multiple_loads_latest(tmp_path):
    store = StateStore(db_path=str(tmp_path / "groupwatch.db"))
    store.save_state("Domain Admins", [_miembro("jperez", "jperez")])
    store.save_state("Domain Admins", [_miembro("jperez", "jperez"), _miembro("rgomez", "rgomez")])
    ultimo = store.load_state("Domain Admins")
    assert ultimo is not None
    assert len(ultimo) == 2
    assert any(m["samaccountname"] == "rgomez" for m in ultimo)


def test_save_event_and_count(tmp_path):
    store = StateStore(db_path=str(tmp_path / "groupwatch.db"))
    assert store.get_today_event_count() == 0
    store.save_event("Domain Admins", "added", "rgomez")
    store.save_event("Domain Admins", "removed", "jperez")
    assert store.get_today_event_count() == 2


def test_persistence_across_instances(tmp_path):
    db_path = str(tmp_path / "groupwatch.db")
    store_a = StateStore(db_path=db_path)
    store_a.save_state("Administrators", [_miembro("admin1", "admin1")])
    store_a.save_event("Administrators", "added", "admin1")

    store_b = StateStore(db_path=db_path)
    recuperado = store_b.load_state("Administrators")
    assert recuperado is not None
    assert len(recuperado) == 1
    assert recuperado[0]["samaccountname"] == "admin1"
    assert store_b.get_today_event_count() == 1
