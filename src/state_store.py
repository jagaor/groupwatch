import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional


class StateStore:
    """Persistencia del estado de grupos privilegiados en SQLite.

    Mantiene el histórico de snapshots por grupo y los eventos de cambio
    detectados, de modo que el DiffEngine pueda comparar contra el estado
    previo y el notificador pueda reportar métricas diarias.
    """

    def __init__(self, db_path: str = "groupwatch.db") -> None:
        self.db_path = db_path
        # Aseguramos el directorio contenedor si se indica una ruta con carpetas
        directorio = os.path.dirname(os.path.abspath(db_path))
        if directorio and not os.path.isdir(directorio):
            os.makedirs(directorio, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self.db_path)
        conexion.row_factory = sqlite3.Row
        return conexion

    def _init_schema(self) -> None:
        """Crea las tablas necesarias si no existen."""
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS group_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_name TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS change_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_name TEXT NOT NULL,
                    added_json TEXT NOT NULL,
                    removed_json TEXT NOT NULL,
                    detected_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_state(self, group_name: str, members: list[dict]) -> None:
        """Serializa y guarda un snapshot del grupo indicado."""
        snapshot_json = json.dumps(members, ensure_ascii=False)
        recorded_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO group_snapshots (group_name, snapshot_json, recorded_at) "
                "VALUES (?, ?, ?)",
                (group_name, snapshot_json, recorded_at),
            )
            conn.commit()

    def load_state(self, group_name: str) -> Optional[list[dict]]:
        """Recupera el snapshot más reciente del grupo o None si no existe."""
        with self._connect() as conn:
            fila = conn.execute(
                "SELECT snapshot_json FROM group_snapshots "
                "WHERE group_name = ? ORDER BY id DESC LIMIT 1",
                (group_name,),
            ).fetchone()
        if fila is None:
            return None
        try:
            return json.loads(fila["snapshot_json"])
        except (json.JSONDecodeError, TypeError):
            return None

    def save_event(self, group_name: str, added: list[dict], removed: list[dict]) -> None:
        """Registra un evento de cambio con los miembros añadidos y eliminados."""
        added_json = json.dumps(added, ensure_ascii=False)
        removed_json = json.dumps(removed, ensure_ascii=False)
        detected_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO change_events (group_name, added_json, removed_json, detected_at) "
                "VALUES (?, ?, ?, ?)",
                (group_name, added_json, removed_json, detected_at),
            )
            conn.commit()

    def get_today_event_count(self) -> int:
        """Cuenta los eventos registrados en la fecha UTC actual."""
        prefijo_hoy = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._connect() as conn:
            fila = conn.execute(
                "SELECT COUNT(*) AS total FROM change_events WHERE detected_at LIKE ?",
                (prefijo_hoy + "%",),
            ).fetchone()
        return int(fila["total"]) if fila is not None else 0
