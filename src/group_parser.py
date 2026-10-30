import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass(frozen=True)
class GroupMember:
    """Representa un miembro normalizado de un grupo privilegiado."""

    cn: str
    sam_account_name: str
    dn: str
    upn: str
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GroupParser:
    """Normaliza las entradas crudas devueltas por LDAP en objetos GroupMember."""

    # Campos reconocidos en las respuestas LDAP-like, con sus posibles alias.
    _FIELD_ALIASES: Dict[str, tuple] = {
        "cn": ("cn", "commonName", "name"),
        "sam_account_name": ("samaccountname", "sAMAccountName", "samAccountName"),
        "dn": ("dn", "distinguishedName"),
        "upn": ("upn", "userPrincipalName", "userprincipalname"),
    }

    def _extract(self, entry: Dict[str, Any], field_name: str) -> str:
        """Busca el primer alias disponible en la entrada y lo normaliza."""
        for alias in self._FIELD_ALIASES[field_name]:
            if alias in entry and entry[alias] is not None:
                value = entry[alias]
                # LDAP puede devolver listas de valores; tomamos el primero.
                if isinstance(value, (list, tuple)):
                    value = value[0] if value else ""
                return str(value).strip()
        return ""

    def _build_member(self, entry: Dict[str, Any], captured_at: datetime) -> GroupMember:
        """Construye un GroupMember a partir de una entrada cruda."""
        return GroupMember(
            cn=self._extract(entry, "cn"),
            sam_account_name=self._extract(entry, "sam_account_name").lower(),
            dn=self._extract(entry, "dn"),
            upn=self._extract(entry, "upn").lower(),
            captured_at=captured_at,
        )

    def parse_entries(self, raw: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[GroupMember]]:
        """Normaliza el diccionario grupo -> lista de entradas crudas."""
        captured_at = datetime.now(timezone.utc)
        parsed: Dict[str, List[GroupMember]] = {}
        for group_name, entries in (raw or {}).items():
            if not entries:
                parsed[group_name] = []
                continue
            parsed[group_name] = [self._build_member(e, captured_at) for e in entries]
        return parsed

    def member_to_dict(self, member: GroupMember) -> Dict[str, Any]:
        """Serializa un GroupMember a un diccionario apto para JSON."""
        return {
            "cn": member.cn,
            "sam_account_name": member.sam_account_name,
            "dn": member.dn,
            "upn": member.upn,
            "captured_at": member.captured_at.isoformat(),
        }

    def member_from_dict(self, d: Dict[str, Any]) -> GroupMember:
        """Reconstruye un GroupMember desde un diccionario serializado."""
        raw_ts = d.get("captured_at")
        if isinstance(raw_ts, datetime):
            captured_at = raw_ts
        elif isinstance(raw_ts, str) and raw_ts:
            captured_at = datetime.fromisoformat(raw_ts)
        else:
            captured_at = datetime.now(timezone.utc)
        return GroupMember(
            cn=str(d.get("cn", "")).strip(),
            sam_account_name=str(d.get("sam_account_name", "")).strip().lower(),
            dn=str(d.get("dn", "")).strip(),
            upn=str(d.get("upn", "")).strip().lower(),
            captured_at=captured_at,
        )
