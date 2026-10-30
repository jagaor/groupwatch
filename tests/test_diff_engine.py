import pytest

from src.diff_engine import DiffEngine


@pytest.fixture
def previous_state():
    return [
        {"dn": "CN=Alice,OU=Admins,DC=corp,DC=local", "cn": "Alice", "sam_account_name": "alice"},
        {"dn": "CN=Bob,OU=Admins,DC=corp,DC=local", "cn": "Bob", "sam_account_name": "bob"},
        {"dn": "CN=Carol,OU=Admins,DC=corp,DC=local", "cn": "Carol", "sam_account_name": "carol"},
    ]


@pytest.fixture
def current_state_no_change(previous_state):
    return [dict(m) for m in previous_state]


@pytest.fixture
def current_state_add(previous_state):
    extra = {"dn": "CN=Dave,OU=Admins,DC=corp,DC=local", "cn": "Dave", "sam_account_name": "dave"}
    return [dict(m) for m in previous_state] + [extra]


@pytest.fixture
def current_state_remove(previous_state):
    return [dict(m) for m in previous_state[1:]]


@pytest.fixture
def current_state_add_remove(previous_state):
    nuevo = {"dn": "CN=Eve,OU=Admins,DC=corp,DC=local", "cn": "Eve", "sam_account_name": "eve"}
    return [dict(m) for m in previous_state[1:]] + [nuevo]


def test_baseline_returns_no_change(current_state_no_change):
    engine = DiffEngine()
    result = engine.compute(previous=None, current=current_state_no_change)
    assert result.has_changes is False
    assert result.added == []
    assert result.removed == []


def test_no_change_returns_false(previous_state, current_state_no_change):
    engine = DiffEngine()
    result = engine.compute(previous=previous_state, current=current_state_no_change)
    assert result.has_changes is False
    assert result.added == []
    assert result.removed == []


def test_member_added_detected(previous_state, current_state_add):
    engine = DiffEngine()
    result = engine.compute(previous=previous_state, current=current_state_add)
    assert result.has_changes is True
    assert len(result.added) == 1
    assert result.added[0]["sam_account_name"] == "dave"
    assert result.removed == []


def test_member_removed_detected(previous_state, current_state_remove):
    engine = DiffEngine()
    result = engine.compute(previous=previous_state, current=current_state_remove)
    assert result.has_changes is True
    assert result.added == []
    assert len(result.removed) == 1
    assert result.removed[0]["sam_account_name"] == "alice"


def test_simultaneous_add_remove(previous_state, current_state_add_remove):
    engine = DiffEngine()
    result = engine.compute(previous=previous_state, current=current_state_add_remove)
    assert result.has_changes is True
    assert len(result.added) == 1
    assert result.added[0]["sam_account_name"] == "eve"
    assert len(result.removed) == 1
    assert result.removed[0]["sam_account_name"] == "alice"


def test_dn_normalization(previous_state):
    engine = DiffEngine()
    # Mismo DN con distinto case no debe considerarse un cambio
    current = [dict(m) for m in previous_state]
    current[0] = dict(current[0])
    current[0]["dn"] = current[0]["dn"].upper()
    result = engine.compute(previous=previous_state, current=current)
    assert result.has_changes is False
    assert result.added == []
    assert result.removed == []
