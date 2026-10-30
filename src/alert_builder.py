from datetime import datetime, timezone
from typing import Dict, List


class AlertBuilder:
    """Construye los mensajes Markdown que se envían por Telegram.

    No depende de módulos externos: solo recibe objetos con los atributos
    esperados (event.added / event.removed con cn y sam_account_name).
    """

    FOOTER = "GroupWatch ITDR Monitor"

    def _format_member(self, member) -> str:
        """Devuelve una línea Markdown con el cn y el samaccountname del miembro."""
        cn = getattr(member, "cn", None) or "(sin cn)"
        sam = getattr(member, "sam_account_name", None) or "(sin samaccountname)"
        return f"- **{cn}** (`{sam}`)"

    def _format_section(self, title: str, members: List) -> str:
        """Formatea una sección de miembros añadidos o eliminados."""
        if not members:
            return f"**{title}**\nNinguno"
        lineas = [self._format_member(m) for m in members]
        return f"**{title}**\n" + "\n".join(lineas)

    def build_message(self, event) -> str:
        """Genera el mensaje de alerta para un evento de cambio de membresía."""
        group_name = getattr(event, "group_name", None) or getattr(event, "group", "desconocido")
        timestamp = getattr(event, "timestamp", None) or datetime.now(timezone.utc)
        if isinstance(timestamp, datetime):
            ts_str = timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        else:
            ts_str = str(timestamp)

        added = getattr(event, "added", []) or []
        removed = getattr(event, "removed", []) or []

        partes = [
            f"⚠️ **Cambio en grupo privilegiado: {group_name}**",
            f"🕒 {ts_str}",
            "",
            self._format_section("AÑADIDOS", added),
            "",
            self._format_section("ELIMINADOS", removed),
            "",
            f"_{self.FOOTER}_",
        ]
        return "\n".join(partes)

    def build_summary(self, group_stats: Dict[str, int]) -> str:
        """Genera un resumen periódico del estado de los grupos vigilados."""
        ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        lineas = ["✅ **GroupWatch: sin cambios**", f"🕒 {ts_str}", ""]
        if group_stats:
            for grupo, total in group_stats.items():
                lineas.append(f"- **{grupo}**: `{total}` miembros")
        else:
            lineas.append("No hay grupos configurados.")
        lineas.append("")
        lineas.append(f"_{self.FOOTER}_")
        return "\n".join(lineas)
