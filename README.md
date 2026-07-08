# LocoNeo5j

> A lightweight, reproducible setup for running **Neo4j Community Edition** on Apple‑silicon Macs using **Colima + Docker Compose**, plus a Python helper that lets you switch between multiple exported `.dump` files without spinning up multiple databases.

This repository is the result of a multi‑session research project that started with a Windows‑machine Neo4j Desktop database and ended up as a portable, containerised setup on macOS. It is intentionally opinionated, small, and easy to read.

---

## What you get

| Component | Purpose |
|-----------|---------|
| `project/docker-compose.yml` | Brings up a single Neo4j container with bind‑mounts for data, logs, plugins, config and import folders. |
| `project/neo4j.conf` | Custom Neo4j configuration: HTTP bind to localhost, GDS‑friendly JVM flag, page cache size, plugin paths, etc. |
| `project/.env` | Holds the Neo4j password (kept out of version control). |
| `conf/neo4j.conf` | A second, shorter config file used by the helper script for ad‑hoc `neo4j-admin load/dump` runs. |
| `neo4j_manager.py` | Interactive CLI that lets you **pick a `.dump` file**, load it, start Neo4j, work with it, and **export a fresh dump** on shutdown. |
| `docs/` | Step‑by‑step guides, troubleshooting, and a blog post. |
| `importneo4j-db-via-docker-on-mac-20260703.json` | Raw transcript of the original research conversation (kept for reference). |

---

## Quick start

```bash
# 1. Install Colima + Docker CLI (one‑off)
brew install colima docker docker-compose
colima start

# 2. Clone this repo and prepare the host folders
git clone https://github.com/<you>/LocoNeo5j.git
cd LocoNeo5j
mkdir -p ~/neo4j/{data,logs,plugins,conf,import}

# 3. Create your password file
cp project/.env.example project/.env
# edit project/.env and set NEO4J_PASSWORD

# 4. Copy any *.dump files you want to load into ~/neo4j/import/

# 5. Launch the interactive helper
python3 neo4j_manager.py
```

The helper will:

1. Detect any running Neo4j container and offer to stop it.
2. List every `*.dump` it finds in `~/neo4j/import/` and ask which one to load.
3. Run `neo4j-admin load` against the named volumes.
4. Start the long‑running Neo4j service.
5. Print the HTTP and Bolt connection info.
6. On Ctrl‑C, optionally export the current database to a fresh dump and shut down.

---

## Repository layout

```
LocoNeo5j/
├── README.md                       # you are here
├── neo4j_manager.py                # interactive import/export helper
├── docs/
│   ├── blog.md                     # the published write‑up
│   ├── setup.md                    # detailed setup walk‑through
│   ├── troubleshooting.md          # every error we hit, plus the fix
│   ├── plugins.md                  # apoc / gds / genai / apoc‑extended
│   └── mcp.md                      # Neo4j MCP server setup for VS Code
├── project/                        # the working docker-compose stack
│   ├── docker-compose.yml
│   ├── neo4j.conf
│   └── .env.example
├── conf/                           # extra config used by the helper script
│   └── neo4j.conf
├── scripts/
│   └── load-all.sh                 # one‑shot loader for many dump files
└── importneo4j-db-via-docker-on-mac-20260703.json
```

---

## Why this exists

The full story is in [`docs/blog.md`](docs/blog.md). The short version:

* Docker Desktop on macOS is heavy. **Colima** is a drop‑in replacement that runs the same Docker daemon in a lightweight Linux VM (~150 MB RAM idle vs. ~1 GB+).
* Running Neo4j in a container means dealing with **UID/GID mismatches** for the bind‑mounted volumes. Pre‑chowning to UID `1001` (the Neo4j user inside the image) is the simplest fix.
* Neo4j Community Edition only allows **one user database**. To work with multiple `.dump` files you either spin up multiple containers or load them sequentially. The helper script does the latter.
* The Neo4j image exposes every `neo4j.conf` setting as an `NEO4J_<UPPER_SNAKE_CASE>` environment variable, but **JVM options** and a few other settings must live in a mounted `neo4j.conf` file.

---

## License

MIT. See [`LICENSE`](LICENSE)
