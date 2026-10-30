from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChangeEvent:
    """Evento que representa el delta de miembros de un grupo privilegiado."""

    group_name: str
    added: list[dict] = field(default_factory=list)
    removed: list[dict] = field(default_factory=list)
    has_changes: bool = False


class DiffEngine:
    """Motor de comparación de snapshots de miembros de grupos de AD.

    La identidad de cada miembro se determina por su campo 'dn'
    normalizado a minúsculas, de modo que diferencias de mayúsculas
    en el DN no generen falsos positivos.
    """

    @staticmethod
    def _normalize_dn(dn: Optional[str]) -> str:
        """Normaliza un DN para usarlo como clave de comparación."""
        if not dn:
            return ""
        return dn.strip().lower()

    def compute_diff(
        self,
        group_name: str,
        previous: Optional[list[dict]],
        current: list[dict],
    ) -> ChangeEvent:
        """Calcula el delta entre el snapshot previo y el actual.

        Si 'previous' es None estamos ante el primer arranque (baseline)
        y no se emite evento de cambio.
        """
        if previous is None:
            return ChangeEvent(group_name=group_name, has_changes=False)

        # Indexamos por DN normalizado para conservar el dict completo original
        prev_map: dict[str, dict] = {}
        for member in previous:
            key = self._normalize_dn(member.get("dn"))
            if key:
                prev_map[key] = member

        curr_map: dict[str, dict] = {}
        for member in current:
            key = self._normalize_dn(member.get("dn"))
            if key:
                curr_map[key] = member

        prev_keys = set(prev_map.keys())
        curr_keys = set(curr_map.keys())

        added_keys = curr_keys - prev_keys
        removed_keys = prev_keys - curr_keys

        added = [curr_map[k] for k in sorted(added_keys)]
        removed = [prev_map[k] for k in sorted(removed_keys)]

        return ChangeEvent(
            group_name=group_name,
            added=added,
            removed=removed,
            has_changes=bool(added or removed),
        )
