# matrix-taskbot

A [Taskwarrior](https://taskwarrior.org/) bot for [Matrix](https://matrix.org/) — query and add tasks from any Matrix client, including mobile.

Send commands to the bot in a Matrix room and get task output back. Works with Element, FluffyChat, and any Matrix client.

## Commands

| Command | Description |
|---------|-------------|
| `help` | Show help |
| `next` | `task next` |
| `list [filter]` | `task [filter] list` |
| `add <description> [+tag] [project:foo] [due:tomorrow]` | Add a task (triggers on-add hooks) |
| `<id>` | `task <id> information` |
| `<filter>` | Any other input is treated as a filter + list |

## Requirements

- Taskwarrior 2.6.x
- Python 3.6+
- [matrix-nio](https://github.com/poljar/matrix-nio): `pip install matrix-nio`
- A Matrix account for the bot (separate from your own)

## Install

### Via awesome-taskwarrior

```bash
tw -I matrix-taskbot
```

### Manual

```bash
pip install matrix-nio
cp matrix-taskbot.py ~/.task/scripts/
cp matrix-taskbot.rc ~/.task/config/
```

## Setup

1. **Create a bot account** — Register a dedicated Matrix account (e.g. `@task-bot:matrix.org`) at [app.element.io](https://app.element.io) or any homeserver.

2. **Edit the config** at `~/.task/config/matrix-taskbot.rc`:

   ```ini
   homeserver   = https://matrix-client.matrix.org
   bot_user     = @task-bot:matrix.org
   allowed_users = @you:matrix.org
   ```

   > **Note:** The homeserver URL is the Matrix Client-Server API endpoint, not the web UI URL. For matrix.org accounts use `https://matrix-client.matrix.org`.

3. **Log in** to save an access token:

   ```bash
   python3 ~/.task/scripts/matrix-taskbot.py --login
   ```

4. **Run the bot:**

   ```bash
   python3 ~/.task/scripts/matrix-taskbot.py
   ```

5. **Create a room** — In your Matrix client, create a new room and invite the bot account. **Disable encryption** when creating the room (the bot cannot decrypt E2E messages without libolm). Invite the bot; it will auto-accept and join.

6. **Send a command** — Try `next` or `help`.

## Configuration

`~/.task/config/matrix-taskbot.rc`:

| Key | Default | Description |
|-----|---------|-------------|
| `homeserver` | `https://matrix-client.matrix.org` | Matrix CS API URL |
| `bot_user` | — | Bot's Matrix user ID (required) |
| `allowed_users` | — | Comma-separated Matrix IDs allowed to use the bot. Empty = anyone |
| `max_output` | `40` | Max lines per reply |
| `task` | `task` | Path to the task binary |

## Running as a service

```ini
# ~/.config/systemd/user/matrix-taskbot.service
[Unit]
Description=matrix-taskbot Taskwarrior bot
After=network-online.target

[Service]
ExecStart=/usr/bin/python3 %h/.task/scripts/matrix-taskbot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now matrix-taskbot
```

## Debugging

```bash
# Print debug info to stderr and log to ~/.task/logs/debug/
python3 ~/.task/scripts/matrix-taskbot.py --debug

# Or via environment variable
TW_DEBUG=2 python3 ~/.task/scripts/matrix-taskbot.py
```

## Notes

- **Hooks:** `add` commands run with hooks enabled so your on-add hooks fire normally. Read-only commands (list, next, info) run with hooks off for speed.
- **Encryption:** matrix.org DMs are encrypted by default. The bot works in unencrypted rooms only (create room → disable encryption before inviting the bot).
- **Security:** Set `allowed_users` to restrict access to your own Matrix ID.

## License

MIT — see [LICENSE](LICENSE)

## Author

linuxcaffe + Claude Sonnet 4.6
