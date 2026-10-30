#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Punto de entrada CLI de GroupWatch.

Autor: Javier Garrido Ortiz

Orquesta el ciclo de sondeo continuo de grupos privilegiados de Active Directory,
comparando snapshots y enviando alertas a Telegram cuando se detectan cambios.
"""

import argparse
import os
import sys
import time
from typing import List

from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ldap_poller import LDAPPoller
from group_parser import GroupParser
from state_store import StateStore
from diff_engine import DiffEngine
from alert_builder import AlertBuilder
from telegram_notifier import TelegramNotifier

# El servidor mock se importa de forma diferida para no requerir FastAPI si no se usa --mock.


def build_arg_parser() -> argparse.ArgumentParser:
    """Construye y devuelve el parser de argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        prog="groupwatch",
        description="Vigilancia continua de grupos privilegiados en Active Directory con alertas a Telegram.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Activa el servidor LDAP simulado (no requiere infraestructura real).",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        metavar="SEGUNDOS",
        help="Intervalo entre sondeos en segundos (por defecto: 60).",
    )
    parser.add_argument(
        "--groups",
        type=str,
        default="Domain Admins,Enterprise Admins,Schema Admins",
        help="Lista de grupos a monitorizar separados por comas.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Activa la salida detallada por consola.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Detecta cambios pero no envía alertas a Telegram.",
    )
    return parser


def print_banner(console: Console) -> None:
    """Imprime el banner de bienvenida de GroupWatch usando Rich."""
    console.print(
        Panel.fit(
            "[bold cyan]GroupWatch[/bold cyan]\n"
            "Vigilancia continua de grupos privilegiados en Active Directory",
            border_style="cyan",
        )
    )


def run_poll_cycle(
    poller: LDAPPoller,
    parser: GroupParser,
    store: StateStore,
    differ: DiffEngine,
    builder: AlertBuilder,
    notifier: TelegramNotifier,
    console: Console,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Ejecuta un ciclo completo de sondeo, comparación y alerta.

    Pasos:
      1. Obtiene las entradas actuales de todos los grupos monitorizados.
      2. Normaliza los DN devueltos por LDAP en objetos Python.
      3. Carga el estado previo desde SQLite.
      4. Calcula el delta entre el estado previo y el actual.
      5. Si hay cambios, construye y envía la alerta (salvo en modo dry-run).
      6. Persiste el nuevo estado.
      7. Muestra un resumen por consola.
    """
    console.rule("[bold]Ciclo de sondeo[/bold]")

    # 1) Adquisición: consulta LDAP de todos los grupos configurados.
    raw_entries = poller.fetch_all_groups()
    if verbose:
        console.print(f"[dim]Entradas LDAP recibidas: {len(raw_entries)}[/dim]")

    # 2) Parsing: normaliza las entradas en objetos con cn, dn, samaccountname y timestamp.
    current_snapshot = parser.parse_entries(raw_entries)

    # 3) Persistencia: carga el estado previo (baseline o último snapshot guardado).
    previous_snapshot = store.load_state()

    # 4) Comparación: calcula el delta entre snapshots.
    diff = differ.compute_diff(previous_snapshot, current_snapshot)

    # 5) Alertas: si hay cambios, construye el mensaje y notifica.
    if diff.has_changes():
        message = builder.build_message(diff)
        if dry_run:
            console.print("[yellow]Modo dry-run: alerta no enviada a Telegram.[/yellow]")
            console.print(message)
        else:
            try:
                notifier.send(message)
                console.print("[green]Alerta enviada a Telegram.[/green]")
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Error al enviar alerta a Telegram: {exc}[/red]")
    else:
        console.print("[dim]Sin cambios detectados.[/dim]")

    # 6) Persistencia: guarda el nuevo snapshot como estado actual.
    store.save_state(current_snapshot)

    # 7) Resumen por consola con Rich.
    table = Table(title="Resumen del ciclo")
    table.add_column("Métrica", style="cyan")
    table.add_column("Valor", style="magenta")
    table.add_row("Grupos monitorizados", str(len(current_snapshot)))
    table.add_row("Miembros totales", str(sum(len(m) for m in current_snapshot.values())))
    table.add_row("Añadidos", str(len(diff.added)))
    table.add_row("Eliminados", str(len(diff.removed)))
    console.print(table)


def main() -> int:
    """Función principal: carga configuración, inicializa módulos y arranca el scheduler."""
    # Carga variables de entorno desde .env (nunca hardcodear secretos).
    load_dotenv()

    args = build_arg_parser().parse_args()
    console = Console()
    print_banner(console)

    # Lista de grupos a monitorizar.
    groups: List[str] = [g.strip() for g in args.groups.split(",") if g.strip()]
    if not groups:
        console.print("[red]Error: no se ha especificado ningún grupo a monitorizar.[/red]")
        return 1

    # Configuración LDAP desde variables de entorno.
    ldap_server = os.getenv("LDAP_SERVER", "ldap://localhost:389")
    ldap_user = os.getenv("LDAP_USER", "")
    ldap_password = os.getenv("LDAP_PASSWORD", "")
    ldap_base_dn = os.getenv("LDAP_BASE_DN", "dc=example,dc=com")

    # Configuración Telegram desde variables de entorno.
    telegram_token = os.getenv("TELEGRAM_TOKEN", "")
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not args.dry_run and (not telegram_token or not telegram_chat_id):
        console.print(
            "[red]Error: TELEGRAM_TOKEN y TELEGRAM_CHAT_ID son obligatorios "
            "salvo en modo --dry-run.[/red]"
        )
        return 1

    # Arranque del servidor LDAP simulado si se solicita.
    if args.mock:
        try:
            from mock_server import start_mock_server

            start_mock_server(host=os.getenv("MOCK_HOST", "127.0.0.1"), port=int(os.getenv("MOCK_PORT", "8000")))
            console.print("[green]Servidor LDAP simulado iniciado.[/green]")
            # Pequeña espera para asegurar que el servidor esté listo.
            time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001
            console.print(f"[red]No se pudo iniciar el servidor mock: {exc}[/red]")
            return 1

    # Inicialización de módulos del pipeline.
    poller = LDAPPoller(
        server=ldap_server,
        user=ldap_user,
        password=ldap_password,
        base_dn=ldap_base_dn,
        groups=groups,
    )
    parser = GroupParser()
    store = StateStore(db_path=os.getenv("STATE_DB_PATH", "groupwatch.db"))
    differ = DiffEngine()
    builder = AlertBuilder()
    notifier = TelegramNotifier(token=telegram_token, chat_id=telegram_chat_id)

    # Captura del baseline inicial antes de arrancar el scheduler.
    console.print("[cyan]Capturando baseline inicial...[/cyan]")
    try:
        initial_entries = poller.fetch_all_groups()
        initial_snapshot = parser.parse_entries(initial_entries)
        if store.load_state() is None:
            store.save_state(initial_snapshot)
            console.print("[green]Baseline inicial guardado.[/green]")
        else:
            console.print("[dim]Baseline existente recuperado.[/dim]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Error al capturar baseline: {exc}[/red]")
        return 1

    # Configuración del scheduler.
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_poll_cycle,
        trigger="interval",
        seconds=args.interval,
        args=[poller, parser, store, differ, builder, notifier, console, args.dry_run, args.verbose],
        id="groupwatch_poll",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    console.print(f"[green]Scheduler iniciado. Intervalo: {args.interval}s[/green]")
    console.print("[dim]Pulsa Ctrl+C para detener.[/dim]")

    try:
        # Modo bloqueante: mantiene el proceso vivo hasta interrupción.
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[yellow]Deteniendo GroupWatch...[/yellow]")
        scheduler.shutdown(wait=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
