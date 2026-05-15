# PteroMCP

A [Model Context Protocol](https://modelcontextprotocol.io/) server that
exposes the [Pterodactyl](https://pterodactyl.io/) and
[Pelican](https://pelican.dev/) game-server panels to MCP-compatible clients
(Claude Desktop, Claude Code, custom agents, etc.).

PteroMCP gives an LLM the ability to inspect users, nodes, allocations,
eggs, mounts, roles, databases and **manage servers end-to-end** — from
creation to power signals, console commands, file edits, backups and
schedules — through the panel's official REST APIs.

It speaks both flavors of the API:

- **Application API** (`/api/application/*`) — admin operations, scoped by an
  *application* key.
- **Client API** (`/api/client/*`) — per-user operations (console, files,
  backups, schedules), scoped by a *client* key.

Both Pterodactyl and its Pelican fork are supported. The panel type is
auto-detected on startup. Pelican-only endpoints (e.g. `/roles`) and
Pterodactyl-only endpoints (e.g. `/locations`, `/nests`) raise clear errors
on the wrong flavor instead of silently failing.

## Quick start

### 1. Install

```bash
git clone https://github.com/Showdown76py/PteroMCP.git
cd PteroMCP
python3 -m pip install -e .
```

Python 3.10+ is required. `pipx install -e .` works too if you prefer an
isolated environment.

Once installed, locate the absolute path of the `pteromcp` binary — both
Claude Desktop and Claude Code spawn it without your shell's `PATH`, so
you'll want this path for the config below:

```bash
which pteromcp
# e.g. /Library/Frameworks/Python.framework/Versions/3.13/bin/pteromcp
```

### 2. Configure

Copy `.env.example` to `.env` and fill in your panel URL plus at least one
API key:

```bash
PTEROMCP_PANEL_URL=https://panel.example.com
PTEROMCP_APPLICATION_KEY=papp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# Optional: PTEROMCP_CLIENT_KEY=ptlc_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

You can get an application key from your panel's admin UI (`Application
API`) and a client key from your user account settings (`API
Credentials`). You only need a client key if you intend to expose the
per-user tools (power signals, console, files, backups, schedules).

### 3. Run

```bash
pteromcp           # or `python -m pteromcp`
```

The server talks MCP over stdio.

#### Claude Desktop

Edit your Claude Desktop config file and add an `mcpServers` entry. The
file lives at:

| OS      | Path                                                                     |
| ------- | ------------------------------------------------------------------------ |
| macOS   | `~/Library/Application Support/Claude/claude_desktop_config.json`        |
| Linux   | `~/.config/Claude/claude_desktop_config.json`                            |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json`                            |

```json
{
  "mcpServers": {
    "pteromcp": {
      "command": "/absolute/path/to/pteromcp",
      "env": {
        "PTEROMCP_PANEL_URL": "https://panel.example.com",
        "PTEROMCP_APPLICATION_KEY": "papp_XXXXXXXXXXXXXXXXXXXXXXXX",
        "PTEROMCP_CLIENT_KEY": "ptlc_XXXXXXXXXXXXXXXXXXXXXXXX"
      }
    }
  }
}
```

Quit Claude Desktop fully (Cmd+Q on macOS) and relaunch — it only re-reads
this file on startup.

> Some internal / preview builds of Claude Desktop manage MCP servers from
> their own settings UI and rewrite this file on launch. If your edits get
> wiped, add the server via `Settings → Developer / Extensions` inside the
> app instead.

#### Claude Code

```bash
claude mcp add pteromcp \
  --scope user \
  --env PTEROMCP_PANEL_URL=https://panel.example.com \
  --env PTEROMCP_APPLICATION_KEY=papp_XXXXXXXXXXXXXXXXXXXXXXXX \
  -- /absolute/path/to/pteromcp
```

`--scope user` registers the server globally instead of just the current
project. Drop the `--env` flags or add more (e.g. `PTEROMCP_CLIENT_KEY`,
`PTEROMCP_READ_ONLY`) as needed.

#### Verify

In either client, ask the model to call the `panel_info` tool. You should
get back something like:

```json
{
  "pteromcp_version": "0.1.0",
  "panel_url": "https://panel.example.com",
  "panel_type": "pelican",
  "application_key_configured": true,
  "client_key_configured": false,
  "read_only": false,
  "enabled_categories": ["allocations", "client", "databases", "eggs",
                         "mounts", "nodes", "roles", "servers", "users"]
}
```

If `panel_type` shows `detection-failed: …`, the URL or the API key is
wrong; the error message tells you which.

## Configuration reference

| Variable                          | Default | Description                                                                                                                                       |
| --------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PTEROMCP_PANEL_URL`              | —       | Base URL of the panel. Required.                                                                                                                  |
| `PTEROMCP_APPLICATION_KEY`        | —       | Admin API key (`ptla_…` on Pterodactyl, `papp_…` on Pelican). Required for the application-surface tools.                                         |
| `PTEROMCP_CLIENT_KEY`             | —       | Per-user API key (`ptlc_…` on both panels). Required for client-surface tools.                                                                    |
| `PTEROMCP_PANEL_TYPE`             | `auto`  | One of `auto`, `pterodactyl`, `pelican`.                                                                                                          |
| `PTEROMCP_TIMEOUT`                | `30`    | HTTP timeout in seconds.                                                                                                                          |
| `PTEROMCP_READ_ONLY`              | `false` | When `true`, the server refuses every mutating tool (POST/PATCH/PUT/DELETE). Useful for exploration.                                              |
| `PTEROMCP_DISABLED_CATEGORIES`    | (empty) | CSV of tool categories to disable: `users`, `nodes`, `servers`, `eggs`, `roles`, `mounts`, `databases`, `allocations`, `client`.                  |

## Tool reference

All 68 tools are grouped by category. Every tool accepts JSON arguments and
returns the panel's JSON payload (occasionally with a confirmation envelope
for mutating endpoints).

### Meta

| Tool         | Description                                                  |
| ------------ | ------------------------------------------------------------ |
| `panel_info` | Detected panel type, base URL, configured keys, enabled cats |

### Users (`/api/application/users`)

| Tool                  | Description                                                       |
| --------------------- | ----------------------------------------------------------------- |
| `users_list`          | List users (search + pagination)                                  |
| `users_get`           | Fetch one user by id                                              |
| `users_get_external`  | Fetch one user by `external_id`                                   |
| `users_create`        | Create a user                                                     |
| `users_update`        | Update a user (full-replace semantics, supply all required fields)|
| `users_delete`        | Delete a user                                                     |

### Nodes (`/api/application/nodes`)

| Tool                  | Description                                                       |
| --------------------- | ----------------------------------------------------------------- |
| `nodes_list`          | List nodes                                                        |
| `nodes_get`           | Fetch one node                                                    |
| `nodes_configuration` | Return the wings/daemon config (includes node token — secret)     |
| `nodes_create`        | Create a node                                                     |
| `nodes_update`        | Update a node                                                     |
| `nodes_delete`        | Delete a node                                                     |

### Allocations (`/api/application/nodes/{id}/allocations`)

| Tool                   | Description                                          |
| ---------------------- | ---------------------------------------------------- |
| `allocations_list`     | List allocations on a node                           |
| `allocations_create`   | Create one or more allocations (ports or port range) |
| `allocations_delete`   | Delete an unassigned allocation                      |

### Servers (`/api/application/servers`)

| Tool                          | Description                                              |
| ----------------------------- | -------------------------------------------------------- |
| `servers_list`                | List servers                                             |
| `servers_get`                 | Fetch one server by numeric id                           |
| `servers_get_external`        | Fetch one server by `external_id`                        |
| `servers_create`              | Create a server                                          |
| `servers_update_details`      | Update name, owner, external id, description             |
| `servers_update_build`        | Update resource limits / allocations / feature limits    |
| `servers_update_startup`      | Update startup command, egg, image, env vars             |
| `servers_suspend`             | Suspend a server                                         |
| `servers_unsuspend`           | Unsuspend a server                                       |
| `servers_reinstall`           | Reinstall a server                                       |
| `servers_delete`              | Delete a server (`force=True` ignores daemon errors)     |

### Eggs / Nests

| Tool         | Description                                                   |
| ------------ | ------------------------------------------------------------- |
| `eggs_list`  | List eggs (with or without nest id)                           |
| `eggs_get`   | Fetch one egg, optionally `include=variables`                 |
| `nests_list` | List nests (Pterodactyl only)                                 |
| `nests_get`  | Fetch one nest                                                |

### Roles (Pelican only)

| Tool           | Description                          |
| -------------- | ------------------------------------ |
| `roles_list`   | List roles                           |
| `roles_get`    | Fetch one role                       |
| `roles_create` | Create a role                        |
| `roles_update` | Rename a role or update description  |
| `roles_delete` | Delete a role                        |

### Mounts

| Tool             | Description           |
| ---------------- | --------------------- |
| `mounts_list`    | List mounts           |
| `mounts_get`     | Fetch one mount       |
| `mounts_create`  | Create a mount        |
| `mounts_update`  | Update a mount        |
| `mounts_delete`  | Delete a mount        |

### Databases (per-server)

| Tool                          | Description                                       |
| ----------------------------- | ------------------------------------------------- |
| `databases_list`              | List databases on a server                        |
| `databases_get`               | Fetch one database                                |
| `databases_create`            | Create a database                                 |
| `databases_reset_password`    | Rotate the database password                      |
| `databases_delete`            | Delete a database                                 |

### Client surface (`/api/client/*` — requires `PTEROMCP_CLIENT_KEY`)

| Tool                          | Description                                                 |
| ----------------------------- | ----------------------------------------------------------- |
| `client_account`              | Account info for the API-key owner                          |
| `client_servers_list`         | List servers visible to the user                            |
| `client_server_get`           | Fetch one server by short identifier                        |
| `client_server_resources`     | Live CPU/memory/disk/network usage                          |
| `client_server_power`         | `start` / `stop` / `restart` / `kill`                       |
| `client_server_command`       | Send a console command                                      |
| `client_server_websocket`     | Short-lived URL + token for live console / commands         |
| `client_files_list`           | List files in a directory                                   |
| `client_files_contents`       | Read a file's contents as a string                          |
| `client_files_write`          | Overwrite a file (creates intermediate dirs)                |
| `client_files_rename`         | Rename / move a list of files                               |
| `client_files_copy`           | Duplicate a file                                            |
| `client_files_delete`         | Delete files or directories                                 |
| `client_files_create_folder`  | Create a folder                                             |
| `client_backups_list`         | List backups                                                |
| `client_backups_create`       | Create a backup (`is_locked`, `ignored_files` supported)    |
| `client_backups_get`          | Fetch a backup by UUID                                      |
| `client_backups_restore`      | Restore a backup (`truncate=True` to wipe first)            |
| `client_backups_delete`       | Delete a backup                                             |
| `client_schedules_list`       | List schedules                                              |
| `client_schedules_get`        | Fetch a schedule                                            |
| `client_schedules_execute`    | Trigger a schedule immediately                              |

## Safety

PteroMCP is just a glue layer — it has the same blast radius as the API keys
you give it. A few features make accidents less likely:

- **Read-only mode**. Set `PTEROMCP_READ_ONLY=true` and every mutating
  request returns a `ReadOnlyError` before touching the panel.
- **Category disable**. Use `PTEROMCP_DISABLED_CATEGORIES=client,users` to
  remove whole groups of tools from the served list.
- **Auto-detection**. Pelican-only / Pterodactyl-only endpoints get a clear
  error instead of silently returning 404.
- **Force-delete is explicit**. `servers_delete(force=False)` is the
  default — `force=True` must be passed by the caller.

The server does not log API keys, but be aware that some panel responses
(notably `nodes_configuration`) include sensitive tokens. Treat its output
as you would a `cat` of the wings config file.

## Development

```bash
python3 -m pip install -e ".[dev]"

# unit tests (fast, no network)
python3 -m pytest -m "not integration"

# integration tests against a real panel
export PTEROMCP_INTEGRATION_URL="https://panel.example.com"
export PTEROMCP_INTEGRATION_APPKEY="papp_XXXX"
# opt-in: also create+force-delete a real server during the run
export PTEROMCP_INTEGRATION_SERVER_TEST=1
python3 -m pytest

# lint
ruff check src tests
```

Layout:

```
src/pteromcp/
  __main__.py        # `python -m pteromcp`
  server.py          # FastMCP assembly
  config.py          # env-based settings
  client.py          # async HTTP wrapper
  errors.py
  tools/
    users.py
    nodes.py
    allocations.py
    servers.py
    eggs.py
    roles.py
    mounts.py
    databases.py
    client_surface.py
```

## License

MIT. See [LICENSE](LICENSE).
