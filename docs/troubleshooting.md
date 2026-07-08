# Troubleshooting

Every error I hit while setting this up, with the fix.

---

## `docker: unknown command: docker compose`

The Docker CLI you installed doesn’t have the Compose V2 plugin.

```bash
brew install docker-compose
mkdir -p ~/.docker/cli-plugins
jq '.cliPluginsExtraDirs = ["/opt/homebrew/lib/docker/cli-plugins"]' \
    ~/.docker/config.json > ~/.docker/config.json.tmp \
  && mv ~/.docker/config.json.tmp ~/.docker/config.json
```

Verify: `docker compose version`.

---

## `WARNING: Plugin "...docker-compose" is not valid: exec format error`

You downloaded the wrong architecture binary. On Apple Silicon you need the **`darwin/arm64`** build.

```bash
rm -f ~/.docker/cli-plugins/docker-compose
curl -L "https://github.com/docker/compose/releases/download/v2.29.2/docker-compose-darwin-arm64" \
     -o ~/.docker/cli-plugins/docker-compose
chmod +x ~/.docker/cli-plugins/docker-compose
xattr -d com.apple.quarantine ~/.docker/cli-plugins/docker-compose 2>/dev/null || true
file ~/.docker/cli-plugins/docker-compose   # → Mach-O 64-bit executable arm64
```

---

## `cp: cannot create regular file '/plugins/...': Permission denied`

The bind-mount is not owned by UID `1001` (the `neo4j` user inside the image).

```bash
chown -R 1001:1001 ~/neo4j/data
chown -R 1001:1001 ~/neo4j/logs
chown -R 1001:1001 ~/neo4j/plugins
```

If you don’t want to chown, switch to Docker-managed named volumes (see `README.md`).

---

## `Failed to read config — Unrecognized setting: server.http.bind.address`

You set an env var with the wrong name. The image uses `NEO4J_<UPPER_SNAKE_CASE>` where dots become underscores. For `dbms.connector.http.bind_address` you must use `NEO4J_dbms_connector_http_bind_address` — **not** `NEO4J_server_http_bind_address`.

Easiest: put the setting in `neo4j.conf` instead.

---

## `NEO4JLABS_PLUGINS has been renamed to NEO4J_PLUGINS since Neo4j 5.0.0`

Rename the env var in your compose file:

```yaml
- NEO4J_PLUGINS=["graph-data-science","genai","apoc"]
```

---

## `WARN [gds] The configuration gds.model.store_location is missing.`

Either set a location or disable GDS metrics.

```conf
# neo4j.conf
gds.model.store_location=/var/lib/neo4j/gds/models
# or
gds.metrics.enabled=false
```

---

## `WARN SECURITY WARNING: X-Forward headers accepted from any source`

Bind the HTTP connector to localhost:

```conf
dbms.connector.http.bind_address=127.0.0.1:7474
```

Docker still maps host port `7474` → container port `7474`, so you can reach it from the host.

---

## `the attribute 'version' is obsolete`

Drop the top-level `version:` key from `docker-compose.yml`. Compose file format 3.x ignores it.

---

## `Bolt enabled on 0.0.0.0:7687` but I can’t connect from another machine

You’re using `bolt://neo4j-hostname:7687` and the hostname doesn’t resolve from the network you’re on. Either:

* Add an entry to `/etc/hosts` pointing at the Mac’s LAN IP, or
* Use the `.local` hostname only when both machines are on the same LAN, or
* Switch to a regular DNS name.

---

## `neo4j-admin load: command not found`

You’re running the command outside the container. Use `docker run --rm ... neo4j:latest neo4j-admin load ...` (see `docs/setup.md`).

---

## MCP server can’t connect

* Check `NEO4J_URL` in `.vscode/mcp.json` — it should be reachable from the host where VS Code runs.
* Make sure the username/password in the prompt match the ones in `project/.env`.
* The Neo4j Bolt listener must be reachable on `0.0.0.0:7687` (it is, by default).
* Test the connection from a terminal:
  ```bash
  cypher-shell -a bolt://localhost:7687 -u neo4j -p <password>
  ```
