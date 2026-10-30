![banner](docs/banner.png)

## Architecture

![architecture](docs/architecture.png)

## Demo

![demo](docs/demo.png)

> 🇪🇸 Lee esto en [español](README.md).

# GroupWatch

Continuous monitoring of privileged groups in Active Directory with instant Telegram alerts.

GroupWatch polls the members of one or more privileged AD groups (Domain Admins, Enterprise Admins, etc.), stores snapshots in SQLite, computes the delta against the previous state, and sends a Markdown-formatted alert to Telegram whenever a member is added or removed. It also prints the event to the console with color via Rich.

## Features

- Continuous polling of privileged groups through LDAP (ldap3).
- Persistent baseline and snapshot history in SQLite.
- Delta computation (added / removed members) between consecutive snapshots.
- Instant Telegram notifications with Markdown formatting.
- Colored console output with Rich.
- Background scheduling with APScheduler (configurable interval).
- Mock mode (`--mock`) that spins up a simulated LDAP server (FastAPI) so the project runs without real infrastructure.
- Configuration exclusively via environment variables (.env with python-dotenv).

## Architecture

GroupWatch is organized as a continuous polling pipeline across five layers:

1. **Acquisition** (`LDAPPoller`): connects to Active Directory with ldap3 and queries the current members of each configured privileged group. In `--mock` mode it starts a simulated LDAP server built with FastAPI that returns LDAP-like JSON responses.
2. **Parsing** (`GroupParser`): normalizes the DNs returned by LDAP into plain Python objects with `cn`, `dn`, `samaccountname` and `timestamp` fields.
3. **Persistence** (`StateStore`): serializes the current state of each group into a SQLite database (`groupwatch.db`), keeping a history of snapshots. On first run it creates the baseline; on later runs it restores it.
4. **Comparison** (`DiffEngine`): computes the delta between the previous snapshot and the current one, producing `added` and `removed` member sets. If the delta is not empty, it emits a change event.
5. **Alerting** (`AlertBuilder` + `TelegramNotifier`): formats the event as an enriched Markdown message and calls the Telegram API (python-telegram-bot) to deliver it to the configured `chat_id`. At the same time, `RichConsoleLogger` prints the event to the console with color.

APScheduler orchestrates the polling cycle every N seconds (configurable) as a background job. The CLI entry point (`main.py`) parses arguments with argparse, loads environment variables from `.env` with python-dotenv, initializes every module, and starts the scheduler in blocking mode.

## Requirements

- Python 3.11
- Access to an Active Directory domain (LDAP over 389 or LDAPS over 636)
- A Telegram bot token and a target chat ID

## Installation

```bash
git clone https://github.com/javiergarrido/groupwatch.git
cd groupwatch
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Available variables:

| Variable | Description | Required |
| --- | --- | --- |
| `LDAP_SERVER` | LDAP server URI (e.g. `ldaps://dc01.corp.local`) | Yes |
| `LDAP_BASE_DN` | Base DN for searches (e.g. `dc=corp,dc=local`) | Yes |
| `LDAP_BIND_DN` | Bind user DN | Yes |
| `LDAP_BIND_PASSWORD` | Bind user password | Yes |
| `LDAP_USE_SSL` | Use LDAPS (`true` / `false`) | No |
| `WATCHED_GROUPS` | Comma-separated list of group CNs to monitor | Yes |
| `POLL_INTERVAL_SECONDS` | Polling interval in seconds | No (default 300) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes |
| `TELEGRAM_CHAT_ID` | Target Telegram chat ID | Yes |
| `DB_PATH` | SQLite database path | No (default `groupwatch.db`) |

No secret is ever hardcoded: everything is read from the environment.

## Usage

Run against a real domain:

```bash
python -m src.main --config .env
```

Run in mock mode (no real LDAP needed):

```bash
python -m src.main --mock --interval 30
```

Available arguments:

- `--config PATH`: path to the `.env` file (default `.env`).
- `--mock`: start the simulated LDAP server instead of connecting to a real one.
- `--interval SECONDS`: override `POLL_INTERVAL_SECONDS`.
- `--once`: run a single polling cycle and exit (useful for cron or testing).

## How the baseline works

On the first run, GroupWatch stores the current members of each group as the baseline. No alert is sent for the initial state. From the second cycle onward, every delta (added or removed member) triggers a Telegram alert and a colored console line.

## Example alert

```
[GroupWatch] Change detected in Domain Admins
Added:
  - jdoe (CN=John Doe,OU=Users,DC=corp,DC=local)
Removed:
  - asmith (CN=Alice Smith,OU=Users,DC=corp,DC=local)
Timestamp: 2024-06-01T12:34:56Z
```

## Running the tests

```bash
pytest -v
```

The test suite covers the diff engine, the state store, and the alert builder. The mock server allows integration tests without a real domain controller.

## Project layout

```
src/
  main.py              CLI entry point and scheduler wiring
  ldap_poller.py       LDAP acquisition layer
  group_parser.py      DN normalization
  state_store.py       SQLite persistence and snapshot history
  diff_engine.py       Snapshot delta computation
  alert_builder.py     Markdown message formatting
  telegram_notifier.py Telegram delivery
  mock_server.py       Simulated LDAP server (FastAPI)
tests/
  test_diff_engine.py
  test_state_store.py
  test_alert_builder.py
```

## Security notes

- Use LDAPS whenever possible to protect bind credentials in transit.
- Bind with a read-only service account restricted to the monitored groups.
- Keep `.env` out of version control (already covered by `.gitignore`).
- Rotate the Telegram bot token if it is ever exposed.

## License

MIT. See [LICENSE](LICENSE).

## Author

Javier Garrido Ortiz
