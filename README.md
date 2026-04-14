# matrix-taskbot

A [Taskwarrior](https://taskwarrior.org/) bot for [Matrix](https://matrix.org/) — query, add, and manage tasks from any Matrix client, including mobile. Includes context switching, location-based context automation, and a one-tap Android companion via HTTP Shortcuts.

Send commands to the bot in a Matrix room and get task output back. Works with Element, Element X, FluffyChat, and any Matrix client.

---

## Commands

| Command | Description |
|---------|-------------|
| `help` | Show help |
| `next` | `task next` |
| `list [filter]` | `task [filter] list` |
| `add <desc> [+tag] [project:foo] [due:tomorrow]` | Add a task (triggers on-add hooks) |
| `<id>` | `task <id> information` |
| `<filter>` | Any other input treated as filter + list |

### Context shortcuts

| Command | Description |
|---------|-------------|
| `@` | Show current context |
| `@name` | Switch to named context |
| `@0` | Clear context |
| `@+name` | Add context to cmx set (requires `tw`) |
| `@-name` | Remove context from cmx set (requires `tw`) |

The bot's Matrix display name updates automatically to reflect the active context, e.g. `taskbot @cmx:need,tod`.

### Dot shortcuts

Resolve to the most recent task — useful for acting on what you just added.

| Shortcut | Resolves to |
|----------|-------------|
| `.` | Most recently added task |
| `..` | Most recently modified task |
| `...` | Most recently completed task |
| `....` | Most recently deleted task |

Example: `. done` completes the task you just added. `.. +urgent` tags the task you last touched.

---

## Requirements

- Taskwarrior 2.6.x
- Python 3.8+
- [matrix-nio](https://github.com/poljar/matrix-nio): `pip install matrix-nio`
- A dedicated Matrix account for the bot (separate from your own)
- `tw` wrapper from [awesome-taskwarrior](https://github.com/linuxcaffe/awesome-taskwarrior) — required for `@+`/`@-` cmx context operations

---

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

---

## Setup

### 1. Create a bot account

Register a dedicated Matrix account (e.g. `@task-bot:matrix.org`) at [app.element.io](https://app.element.io) or your homeserver. Keep this separate from your personal account.

### 2. Configure the bot

Edit `~/.task/config/matrix-taskbot.rc`:

```ini
homeserver    = https://matrix-client.matrix.org
bot_user      = @task-bot:matrix.org
bot_name      = taskbot           # base display name (optional)
allowed_users = @you:matrix.org
max_output    = 40
task          = task              # path to task binary
```

> **Note:** The homeserver URL is the Matrix Client-Server API endpoint. For matrix.org accounts use `https://matrix-client.matrix.org`, not `https://matrix.org`.

### 3. Log in to save credentials

```bash
python3 ~/.task/scripts/matrix-taskbot.py --login
```

### 4. Create a room

In your Matrix client, create a new room and invite the bot account.

> **Important:** Disable encryption when creating the room — the bot cannot decrypt E2E messages. For an existing encrypted DM, create a new unencrypted room instead.

The bot will auto-accept invites from `allowed_users` and join.

### 5. Run the bot

```bash
python3 ~/.task/scripts/matrix-taskbot.py
```

Send `help` or `next` to confirm it's working.

---

## Configuration reference

`~/.task/config/matrix-taskbot.rc`:

| Key | Default | Description |
|-----|---------|-------------|
| `homeserver` | `https://matrix-client.matrix.org` | Matrix CS API endpoint |
| `bot_user` | — | Bot's Matrix user ID (required) |
| `bot_name` | localpart of `bot_user` | Base display name |
| `allowed_users` | — | Comma-separated Matrix IDs. Empty = anyone in the room |
| `max_output` | `40` | Max lines per reply |
| `task` | `task` | Path to Taskwarrior binary |
| `location_context` | `yes` | Enable location-based context switching (`yes`/`no`) |
| `location.name` | — | Zone definition — see Location section below |

---

## Location-based context switching

The bot listens for Matrix location events and automatically switches your Taskwarrior context using cmx (`@+`/`@-`) when you enter or leave defined zones.

Uses **Element's live location sharing** (paperclip → Live location → choose duration). No extra app required — your phone sends periodic location beacons to the bot room while sharing is active.

### Zone configuration

Add zone entries to `matrix-taskbot.rc`. Three formats are supported:

```ini
location_context = yes

# Positive zone: inside radius → @+context
location.home  = 51.5074,-0.1278,200,home      # within 200m of coords
location.work  = 51.5000,-0.1200,300,work

# Negative zone: outside radius → @+context
location.out   = 51.5074,-0.1278,-200,out      # beyond 200m of home coords

# Catch-all: fires when no other zone matches
location.other = out
```

**Format:** `lat,lon,radius_metres,context_name`
**Negative radius:** inverts the match — context fires when you are *outside* that distance.
**Catch-all:** a single context name with no coordinates. Use `location.other` or any name.

**Priority order when multiple zones could apply:**
1. Positive zones (inside radius) — wins first
2. Negative zones (outside radius)
3. Catch-all

So if you have `home` (positive) and `out` (negative, same coords), entering the home radius activates `home` and suppresses `out` automatically.

### How it works

- **Entering** a zone: `@+context` added to cmx set, display name updates
- **Leaving** all zones: `@-context` removed from cmx set
- Bot sends a brief notice in the room: `[location] entered home` / `[location] left home`
- Only processes location events from `allowed_users`

To disable without removing zone definitions:

```ini
location_context = no
```

---

## HTTP Shortcuts companion app (Android)

[HTTP Shortcuts](https://play.google.com/store/apps/details?id=ch.rmy.android.http_shortcuts) (free, no ads) gives you one-tap home screen buttons that send commands to the bot — quick-add dialog, task next, context switcher — without opening Element.

### Step 1 — Get your room ID

You need the internal Matrix room ID (not the room name). Find it one of these ways:

- **Element Web** ([app.element.io](https://app.element.io)): open the DM room with the bot → Room settings (gear icon) → Advanced → "Internal room ID"
- **Copy room link** in any client: the link will look like `https://matrix.to/#/!abc123:matrix.org` — the room ID is `!abc123:matrix.org`

URL-encode it for use in HTTP Shortcuts: replace `!` with `%21` and `:` with `%3A`.
Example: `!abc123:matrix.org` → `%21abc123%3Amatrix.org`

### Step 2 — Create variables

In HTTP Shortcuts: Menu (≡) → Variables → add these:

| Name | Type | Value |
|------|------|-------|
| `hs` | Constant | `https://matrix-client.matrix.org` |
| `mx_user` | Constant | your Matrix localpart (e.g. `djp`) |
| `mx_token` | Constant | *(leave blank — Login shortcut fills it)* |
| `mx_room` | Constant | your URL-encoded room ID |

### Step 3 — Create the Login shortcut

This shortcut fetches and stores your access token. Run it once; re-run if the token ever expires.

1. Create shortcut → name it **Matrix Login**
2. Method: `POST`
3. URL: `{hs}/_matrix/client/v3/login`
4. Headers: `Content-Type: application/json`
5. Request body (JSON):
   ```json
   {
     "type": "m.login.password",
     "identifier": {"type": "m.id.user", "user": "{mx_user}"},
     "password": "{password}"
   }
   ```
6. Pre-request variable: add a **Text Input** variable named `password`, enable **Password mode** (masked). It prompts each run and is never stored.
7. **Scripting tab → Run on Response:**
   ```javascript
   const data = JSON.parse(response.body);
   if (response.statusCode === 200) {
       setVariable('mx_token', data.access_token);
       showToast('Logged in ✓');
   } else {
       showToast('Login failed: ' + (data.errcode || response.statusCode));
       abort();
   }
   ```
8. Run it once — enter your Matrix password when prompted. `mx_token` is now stored.

### Step 4 — Create task shortcuts

All shortcuts share the same base settings:

| Field | Value |
|-------|-------|
| Method | `POST` |
| URL | `{hs}/_matrix/client/v3/rooms/{mx_room}/send/m.room.message/{timestamp}` |
| Header | `Authorization: Bearer {mx_token}` |
| Header | `Content-Type: application/json` |

The `{timestamp}` variable is built into HTTP Shortcuts and satisfies Matrix's unique transaction ID requirement.

---

**Quick Add**

| Field | Value |
|-------|-------|
| Name | Add Task |
| Body | `{"msgtype":"m.text","body":"add {input}"}` |
| Pre-request | Text Input variable `input`, prompt: "Add task:" |
| Feedback | Toast: "Added ✓" |

---

**Task Next**

| Field | Value |
|-------|-------|
| Name | Next |
| Body | `{"msgtype":"m.text","body":"next"}` |
| Feedback | Toast: "Sent — check Element for reply" |

---

**Context Switcher**

| Field | Value |
|-------|-------|
| Name | Context |
| Body | `{"msgtype":"m.text","body":"@{ctx}"}` |
| Pre-request | Selection variable `ctx` with your context names (e.g. `home`, `work`, `need`, `out`) |
| Feedback | Toast: "Context → {ctx}" |

---

### Step 5 — Add to home screen

Long-press each shortcut in HTTP Shortcuts → **Add to Home Screen**. You now have one-tap task controls without opening Element.

---

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

---

## Debugging

```bash
# Log debug output to ~/.task/logs/debug/
TW_DEBUG=2 python3 ~/.task/scripts/matrix-taskbot.py
```

Debug session logs appear at `~/.task/logs/debug/matrix-taskbot_debug_YYYYMMDD_HHMMSS.log`.

---

## Notes

- **Hooks:** `add` commands run with hooks enabled so your on-add hooks fire normally. Read commands run with hooks off for speed.
- **Encryption:** The bot works in unencrypted rooms only. Matrix DMs are encrypted by default — create an explicit unencrypted room for the bot.
- **Security:** Always set `allowed_users` to restrict access to your own Matrix ID.
- **cmx context:** `@+`/`@-` operations require the `tw` wrapper from awesome-taskwarrior. Plain `@name` / `@0` work with bare `task`.
- **Location beacons:** Element X and Element Android both support live location sharing. Beacon interval is set by the client (typically 5–30 seconds).

---

## License

MIT — see [LICENSE](LICENSE)

## Author

linuxcaffe + Claude Sonnet 4.6
