# From Neo4j Desktop on Windows to a Lightweight Docker Stack on Apple Silicon — a Field Report

> **TL;DR** — You can run Neo4j Community Edition on an M‑series Mac without Docker Desktop, switch between multiple exported `.dump` files with a 100‑line Python script, and connect it to VS Code's MCP servers in well under an hour. The trick is knowing about three things: **Colima**, **UID `1001`**, and the **`NEO4J_<UPPER_SNAKE_CASE>` env‑var convention**.

This post is the written‑up version of a multi‑session research conversation that started with a Windows machine running Neo4j Desktop and ended with a portable, containerised setup on macOS. Everything below is reproducible; the repo is at [github.com/<you>/LocoNeo5j](../README.md).

---

## 1. Why I left Docker Desktop behind

Docker Desktop on macOS works, but it ships a HyperKit VM plus a stack of background services (VPN‑kit, DNS, Kubernetes, extensions). Idle RAM usage sits around **800 MB–1.5 GB**, which is a lot for a laptop that mostly runs Neo4j.

**Colima** is a thin CLI wrapper around the same Docker daemon, but it uses Apple’s Virtualization framework through **Lima**. Idle RAM drops to **150–250 MB**. The `docker` CLI behaves exactly the same; the only thing missing out of the box is the Compose plugin, which is a one‑line install:

```bash
brew install colima docker docker-compose
colima start
docker context ls          # should show "colima" as the active context
docker compose version     # should print a version number
```

> **Tip:** if `docker compose version` fails with `unknown command: docker compose`, you’re missing the Compose V2 plugin. Install it via `brew install docker-compose` and add `cliPluginsExtraDirs` to `~/.docker/config.json`:
>
> ```json
> { "cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"] }
> ```

---

## 2. The official Neo4j image already supports ARM64

`docker pull neo4j:latest` on an M‑series Mac automatically fetches the `linux/arm64` variant. No emulation, no Rosetta. The image runs the Neo4j JVM process as user `neo4j` (UID `1001`, GID `1001`) — keep that number in mind, it’s the source of most “Permission denied” errors.

---

## 3. The three‑folder layout that survives restarts

```bash
mkdir -p ~/neo4j/{data,logs,plugins,conf,import}
# Pre‑chown to the neo4j user inside the container
chown -R 1001:1001 ~/neo4j/{data,logs,plugins}
```

| Host path         | Container path        | Purpose                                                                 |
| ----------------- | --------------------- | ----------------------------------------------------------------------- |
| `~/neo4j/data`    | `/data`               | Stores the actual graph store (`databases/`, `transactions/`, `dbms/`). |
| `~/neo4j/logs`    | `/logs`               | Neo4j logs.                                                             |
| `~/neo4j/plugins` | `/plugins`            | Where the image copies the plugin JARs at first start.                  |
| `~/neo4j/conf`    | `/conf`               | Custom `neo4j.conf` (see §5).                                           |
| `~/neo4j/import`  | `/import` (read‑only) | Where you drop `.dump` files to load.                                   |

The bind‑mounts are persisted on the host, so `docker compose down` does **not** wipe your data.

---

## 4. The compose file that works

```yaml
services:
  neo4j:
    image: neo4j:trixie
    container_name: neo4j
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_ACCEPT_LICENSE_AGREEMENT=yes
      - NEO4J_PLUGINS=["graph-data-science","genai","apoc"]
      - NEO4J_CONF=/conf
    volumes:
      - $HOME/neo4j/data:/data
      - $HOME/neo4j/logs:/logs
      - $HOME/neo4j/plugins:/plugins
      - $HOME/neo4j/conf:/conf:ro
      - $HOME/neo4j/import:/import:ro
    restart: unless-stopped
```

The password lives in `project/.env` (kept out of git) and is substituted at compose‑time.

### A few things that bit me

* **`NEO4JLABS_PLUGINS` was renamed to `NEO4J_PLUGINS`** in Neo4j 5.x. The old name still works but logs a deprecation warning.
* **JVM options can’t be set via env vars.** `server.jvm.additional=…` has to live in `neo4j.conf`.
* **The `version:` key at the top of compose files is obsolete.** Drop it.
* The image accepts every `neo4j.conf` setting as an env var of the form `NEO4J_<UPPER_SNAKE_CASE>`. Dots become underscores. Example: `dbms.connector.http.bind_address` → `NEO4J_dbms_connector_http_bind_address`. If you mistype the variable name the container will refuse to start with `Unrecognized setting`.

---

## 5. The minimal `neo4j.conf`

```conf
# HTTP connector — bind to localhost to silence X-Forward warnings
dbms.connector.http.bind_address=127.0.0.1:7474

# macOS-specific GDS workaround (Apple Silicon or Intel)
server.jvm.additional=-Djol.skipHotspotSAAttach=true

# Memory
server.memory.pagecache.size=512M

# Networking
server.default_listen_address=0.0.0.0

# Plugin / log / import directories
server.directories.plugins=/plugins
server.directories.logs=/logs
server.directories.import=/import

# Allow GDS procedures (Community Edition)
dbms.security.procedures.unrestricted=gds.*

# Disable anonymous usage data
dbms.usage_report.enabled=false
```

The `server.jvm.additional=-Djol.skipHotspotSAAttach=true` line is **required** by the GDS plugin on macOS — without it the JVM fails to attach a HotSpot Serviceability Agent and the plugin refuses to load.

---

## 6. Importing a `.dump`

```bash
docker compose down
docker run --rm \
  -v neo4j_data:/data -v neo4j_logs:/logs -v neo4j_plugins:/plugins \
  -v ~/neo4j/import:/import:ro \
  -v ~/LocoNeo5j/conf/neo4j.conf:/var/lib/neo4j/conf/neo4j.conf:ro \
  neo4j:latest \
  neo4j-admin load --from=/import/your-dump.dump --database=neo4j --force
docker compose up -d
```

The `--force` flag is needed because the store is empty after `docker compose down` and you want to overwrite any previous load.

### What about multiple dumps?

Neo4j Community Edition only allows **one user database**. To switch between projects I wrote a tiny Python helper (`neo4j_manager.py` in the repo) that:

1. Lists every `.dump` in `~/neo4j/import/`.
2. Loads the one you pick.
3. Starts Neo4j.
4. On Ctrl‑C, optionally exports a fresh dump and tears the stack down.

If you want to **accumulate** multiple dumps into a single database, drop the `--force` flag for everything after the first — `neo4j-admin load` will append and skip duplicates by ID.

---

## 7. Plugins — what they do and the licensing caveats

| Plugin               | Purpose                                                 | License                                                            |
| -------------------- | ------------------------------------------------------- | ------------------------------------------------------------------ |
| `apoc`               | Utility procedures (JSON, CSV, paths, periodic jobs, …) | Apache 2.0                                                         |
| `graph-data-science` | GDS algorithms (PageRank, Louvain, embeddings, …)       | Community‑GDS is free; some procedures need Enterprise             |
| `genai`              | LLM procedures (chat, embeddings, vector search)        | Neo4j Labs — free, but you must comply with the LLM provider’s TOS |
| `apoc-extended`      | Enterprise‑only APOC procedures (LDAP, backup, …)       | Needs a Neo4j Enterprise license                                   |

For a small dev box you can run `["graph-data-science","genai","apoc"]` safely. Add `apoc-extended` only if you have an Enterprise license — otherwise the procedures simply won’t be available and you’ll see warnings.

---

## 8. Connecting VS Code’s MCP servers

Add a `.vscode/mcp.json` with two servers:

```json
{
  "inputs": [
    { "id": "NEOMEMORY_PASSWORD", "type": "promptString", "password": true,
      "description": "Password for NeoMemory" },
    { "id": "NEOMEMORY_USERNAME", "type": "promptString",
      "description": "Username for NeoMemory" }
  ],
  "servers": {
    "neomemory": {
      "command": "uvx",
      "args": ["mcp-neo4j-memory@0.4.5"],
      "env": {
        "NEO4J_URL": "bolt://neo4j-hostname:7687",
        "NEO4J_DATABASE": "neo4j",
        "NEO4J_USERNAME": "${input:NEOMEMORY_USERNAME}",
        "NEO4J_PASSWORD": "${input:NEOMEMORY_PASSWORD}"
      }
    },
    "neo4j-data-modeling": {
      "command": "uvx",
      "args": ["mcp-neo4j-data-modeling@0.8.2", "--transport", "stdio"]
    }
  }
}
```

The `neo4j-hostname` hostname only resolves on the local network, which is fine for a single‑machine setup. After VS Code prompts you for the credentials once, the `mcp__neomemory__*` tools become available to Copilot — `read_graph`, `create_entities`, `search_memories`, etc.

---

## 9. Edge cases I hit (so you don’t have to)

| Symptom                                                                         | Cause                                                                                                    | Fix                                                                                       |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `docker: unknown command: docker compose`                                       | Compose V2 plugin missing                                                                                | `brew install docker-compose` + add `cliPluginsExtraDirs` to `~/.docker/config.json`      |
| `WARNING: Plugin "...docker-compose" is not valid: exec format error`           | Wrong arch binary downloaded                                                                             | Re‑download `docker-compose-darwin-arm64` from a specific release tag (not `latest`)      |
| `cp: cannot create regular file '/plugins/...': Permission denied`              | Bind‑mount owned by host user, not UID 1001                                                              | `chown -R 1001:1001 ~/neo4j/{data,logs,plugins}`                                          |
| `Unrecognized setting. No declared setting with name: server.http.bind.address` | Env‑var name typo (`NEO4J_server_http_bind_address` instead of `NEO4J_dbms_connector_http_bind_address`) | Use the correct snake‑case name, or move the setting into `neo4j.conf`                    |
| `WARN [gds] The configuration gds.model.store_location is missing.`             | GDS metrics enabled but no store location set                                                            | Either set `gds.model.store_location` or disable metrics with `gds.metrics.enabled=false` |
| `WARN SECURITY WARNING: X-Forward headers accepted from any source`             | HTTP bound to `0.0.0.0` without `allow_proxies`/`allow_hosts`                                            | Bind to `127.0.0.1:7474` (Docker still maps the host port)                                |

---

## 10. What’s in the repo

```
LocoNeo5j/
├── README.md
├── neo4j_manager.py          # interactive dump picker
├── docs/
│   ├── blog.md               # this post
│   ├── setup.md
│   ├── troubleshooting.md
│   ├── plugins.md
│   └── mcp.md
├── project/
│   ├── docker-compose.yml
│   ├── neo4j.conf
│   └── .env.example
├── conf/
│   └── neo4j.conf            # used by neo4j_manager.py for ad-hoc load/dump
├── scripts/
│   └── load-all.sh           # one-shot loader for many dumps
└── importneo4j-db-via-docker-on-mac-20260703.json   # raw transcript
```

---

## 11. What I’d do differently next time

* Skip the bind‑mount ownership dance and use **named volumes** from day one. The `chown` warning is harmless but noisy.
* Write the `neo4j.conf` first, then the compose file. Trying to set everything via env vars leads to typos like the one in row 4 above.
* Keep the password in a `.env` file from the start, not in the compose file as a literal. (I did eventually move it.)
* Use the `mcp-neo4j-memory` server for storing the *learnings* of the conversation itself — it’s a great way to make the research reusable later.

---

## 12. References

* [Neo4j Docker Hub](https://hub.docker.com/_/neo4j) — official image with ARM64 support.
* [Neo4j Docker operations manual](https://neo4j.com/docs/operations-manual/current/docker/introduction/).
* [GDS installation guide](https://neo4j.com/docs/graph-data-science/current/installation/) — covers the macOS JVM flag.
* [Colima](https://github.com/abiosoft/colima) — Docker for macOS without Desktop.
* [Setapp — Docker Desktop alternatives for Mac](https://setapp.com/app-reviews/docker-desktop-alternatives-for-mac) and [Portainer blog](https://www.portainer.io/blog/docker-desktop-alternatives) — the comparison that nudged me away from Docker Desktop.
* [mcp-neo4j-memory](https://github.com/neo4j/mcp-neo4j-memory) — the MCP server I used to store this very write‑up as a knowledge graph.
