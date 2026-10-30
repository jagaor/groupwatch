import pytest

from src.alert_builder import AlertBuilder
from src.group_parser import GroupMember


def _member(cn: str, sam: str) -> GroupMember:
    return GroupMember(
        cn=cn,
        dn=f"CN={cn},OU=Privileged,DC=corp,DC=local",
        samaccountname=sam,
        timestamp="2024-01-01T00:00:00+00:00",
    )


@pytest.fixture
def builder() -> AlertBuilder:
    return AlertBuilder()


def test_build_message_contains_group_name(builder: AlertBuilder) -> None:
    msg = builder.build_message(
        group_name="Domain Admins",
        added=[_member("Ana Lopez", "alopez")],
        removed=[],
    )
    assert "Domain Admins" in msg


def test_build_message_added_section(builder: AlertBuilder) -> None:
    msg = builder.build_message(
        group_name="Domain Admins",
        added=[_member("Ana Lopez", "alopez")],
        removed=[],
    )
    assert "alopez" in msg
    assert "Ana Lopez" in msg


def test_build_message_removed_section(builder: AlertBuilder) -> None:
    msg = builder.build_message(
        group_name="Enterprise Admins",
        added=[],
        removed=[_member("Carlos Ruiz", "cruiz")],
    )
    assert "cruiz" in msg
    assert "Carlos Ruiz" in msg


def test_build_message_empty_added(builder: AlertBuilder) -> None:
    msg = builder.build_message(
        group_name="Schema Admins",
        added=[],
        removed=[_member("Carlos Ruiz", "cruiz")],
    )
    assert "Ninguno" in msg


def test_build_message_empty_removed(builder: AlertBuilder) -> None:
    msg = builder.build_message(
        group_name="Schema Admins",
        added=[_member("Ana Lopez", "alopez")],
        removed=[],
    )
    assert "Ninguno" in msg


def test_build_summary_ok(builder: AlertBuilder) -> None:
    summary = builder.build_summary(
        group_name="Domain Admins",
        added=[_member("Ana Lopez", "alopez")],
        removed=[_member("Carlos Ruiz", "cruiz")],
    )
    assert isinstance(summary, str)
    assert summary.strip() != ""
