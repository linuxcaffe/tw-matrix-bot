#!/usr/bin/env python3
"""
tw-matrix-bot - Taskwarrior Matrix bot
Version: 0.1.0

Listens for commands in Matrix DMs and runs Taskwarrior queries/adds.

Usage:
  python3 tw-matrix-bot.py           # run bot (uses saved credentials)
  python3 tw-matrix-bot.py --login   # first-time login, saves access token

Commands (send in DM to bot):
  help               this message
  list [filter]      task [filter] list
  next               task next
  add <description>  task add <description> [+tag] [project:foo]
  <id>               task <id> information

Install:
  pip install matrix-nio
  cp tw-matrix-bot.py ~/.task/scripts/
  cp tw-matrix-bot.rc ~/.task/config/   # then edit it
  python3 ~/.task/scripts/tw-matrix-bot.py --login
  python3 ~/.task/scripts/tw-matrix-bot.py
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

VERSION     = '0.1.0'
CONFIG_FILE = Path.home() / '.task' / 'config' / 'tw-matrix-bot.rc'
CREDS_FILE  = Path.home() / '.task' / 'config' / '.tw-matrix-bot.creds'

HELP_TEXT = f"""\
tw-matrix-bot v{VERSION} — Taskwarrior from Matrix

  help               this message
  list [filter]      task [filter] list
  next               task next
  add <description>  task add (pass tags, projects etc. as normal)
  <id>               task <id> information
""".strip()


# ── Config ────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    cfg = {
        'homeserver':    'https://matrix.org',
        'bot_user':      '',
        'allowed_users': '',
        'max_output':    '40',
        'task':          'task',
    }
    if not CONFIG_FILE.exists():
        return cfg
    for line in CONFIG_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            key, _, val = line.partition('=')
            cfg[key.strip()] = val.strip()
    return cfg


# ── Credentials ───────────────────────────────────────────────────────────────

def load_creds() -> dict:
    if CREDS_FILE.exists():
        return json.loads(CREDS_FILE.read_text())
    return {}


def save_creds(access_token: str, device_id: str):
    CREDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDS_FILE.write_text(json.dumps({
        'access_token': access_token,
        'device_id':    device_id,
    }))
    CREDS_FILE.chmod(0o600)


# ── Task runner ───────────────────────────────────────────────────────────────

def run_task(task_bin: str, args: list, max_lines: int = 40) -> str:
    try:
        result = subprocess.run(
            [task_bin, 'rc.hooks=off', 'rc.color=off', 'rc.verbose=label,blank']
            + args,
            capture_output=True, text=True, timeout=15,
        )
        out = (result.stdout + result.stderr).strip()
        if not out:
            return '(no output)'
        lines = out.splitlines()
        if len(lines) > max_lines:
            lines = lines[:max_lines] + [f'… ({len(lines) - max_lines} more lines)']
        return '\n'.join(lines)
    except subprocess.TimeoutExpired:
        return '[error] task timed out'
    except Exception as e:
        return f'[error] {e}'


# ── Command parser ────────────────────────────────────────────────────────────

def handle_command(body: str, cfg: dict) -> str:
    body  = body.strip()
    lower = body.lower()
    task  = cfg['task']
    maxl  = int(cfg.get('max_output', 40))

    if lower in ('help', '?', 'h'):
        return HELP_TEXT

    if lower in ('next', 'n'):
        return run_task(task, ['next'], maxl)

    if lower.startswith('add '):
        rest = body[4:].strip()
        if not rest:
            return 'Usage: add <description> [+tag] [project:foo] [due:tomorrow]'
        return run_task(task, ['add'] + rest.split(), maxl)

    if lower.startswith('list') or lower.startswith('ls'):
        parts = body.split(None, 1)
        filter_args = parts[1].split() if len(parts) > 1 else []
        return run_task(task, filter_args + ['list'], maxl)

    # bare number → task info
    if body.isdigit():
        return run_task(task, [body, 'information'], maxl)

    # fallback: treat as filter + list
    return run_task(task, body.split() + ['list'], maxl)


# ── Bot ───────────────────────────────────────────────────────────────────────

async def run_bot(cfg: dict, creds: dict):
    from nio import AsyncClient, RoomMessageText, InviteEvent

    allowed = {u.strip() for u in cfg['allowed_users'].split(',') if u.strip()}

    client            = AsyncClient(cfg['homeserver'], cfg['bot_user'])
    client.access_token = creds['access_token']
    client.device_id    = creds['device_id']
    client.user_id      = cfg['bot_user']

    async def on_message(room, event):
        if not isinstance(event, RoomMessageText):
            return
        if event.sender == cfg['bot_user']:
            return
        if allowed and event.sender not in allowed:
            return
        reply = handle_command(event.body, cfg)
        await client.room_send(
            room_id      = room.room_id,
            message_type = 'm.room.message',
            content      = {'msgtype': 'm.text', 'body': reply},
        )

    async def on_invite(room_id, event):
        if allowed and event.sender not in allowed:
            return
        await client.join(room_id)

    client.add_event_callback(on_message, RoomMessageText)
    client.add_event_callback(on_invite,  InviteEvent)

    print(f'[tw-matrix-bot] v{VERSION} running as {cfg["bot_user"]}')
    print(f'[tw-matrix-bot] allowed users: {cfg["allowed_users"] or "(anyone)"}')
    await client.sync_forever(timeout=30_000, full_state=True)


# ── Login helper ──────────────────────────────────────────────────────────────

async def do_login(cfg: dict):
    from nio import AsyncClient, LoginResponse
    import getpass

    client   = AsyncClient(cfg['homeserver'], cfg['bot_user'])
    password = getpass.getpass(f'Password for {cfg["bot_user"]}: ')
    resp     = await client.login(password)

    if not isinstance(resp, LoginResponse):
        print(f'Login failed: {resp}')
        await client.close()
        sys.exit(1)

    save_creds(resp.access_token, resp.device_id)
    print(f'[tw-matrix-bot] Logged in. Credentials saved to {CREDS_FILE}')
    await client.close()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    cfg = load_config()

    if not cfg['bot_user']:
        print(f'Edit {CONFIG_FILE} and set bot_user, homeserver, allowed_users')
        sys.exit(1)

    if '--login' in sys.argv:
        asyncio.run(do_login(cfg))
        return

    creds = load_creds()
    if not creds.get('access_token'):
        print('No credentials found. Run with --login first.')
        sys.exit(1)

    try:
        asyncio.run(run_bot(cfg, creds))
    except KeyboardInterrupt:
        print('\n[tw-matrix-bot] stopped')


if __name__ == '__main__':
    main()
