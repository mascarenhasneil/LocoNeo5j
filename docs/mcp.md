# MCP — connecting VS Code to Neo4j

VS Code can talk to a Neo4j instance through the **Model Context Protocol**. Two servers are useful:

| Server                    | What it does                                                                  |
| ------------------------- | ----------------------------------------------------------------------------- |
| `mcp-neo4j-memory`        | A persistent knowledge graph of entities + relations, queryable from Copilot. |
| `mcp-neo4j-data-modeling` | Tools for designing graph schemas (Arrows‑style modelling).                   |

---

## 1. Configure the servers

Create `.vscode/mcp.json` at the root of this repo:

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

> The `neo4j-hostname` hostname only resolves on the local network. For a single‑machine setup you can replace it with `localhost`.

VS Code will prompt you for the username and password the first time you invoke a tool from either server. The values get stored securely in your user settings.

---

## 2. Confirm the connection

From VS Code’s Copilot Chat, ask:

> “Use the neomemory MCP server to read the graph.”

A successful call returns `{"entities": [], "relations": []}` for an empty database. If you see an error, jump to the troubleshooting section below.

---

## 3. Try a write

> “Create an entity named ‘LocoNeo5j setup’ of type ‘project’ with the observation ‘Lightweight Neo4j on Apple Silicon via Colima.’”

Then read the graph again — the entity should be there.

---

## 4. Using the database from Cypher

Once the MCP server is connected, you can run Cypher queries against the same Neo4j instance from:

* The Neo4j Browser (`http://localhost:7474`).
* The MCP tools from Copilot (`mcp__neomemory__read_neo4j_cypher`, etc.).
* Any Bolt driver (Python, JavaScript, Java, …) using `bolt://localhost:7687`.

---

## 5. Troubleshooting

| Symptom                                    | Fix                                                                                                 |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| `Failed to connect to Neo4j at bolt://...` | Make sure Neo4j is running (`docker compose ps`) and the hostname resolves (`ping masc…`).          |
| `Authentication failed`                    | The username/password you typed in the VS Code prompt don’t match `project/.env`.                   |
| `Database does not exist`                  | Change `NEO4J_DATABASE` to a database that exists. Community Edition only has `neo4j` and `system`. |
| Tools disappear after VS Code restart      | VS Code re‑prompts for the inputs; just enter them again.                                           |

---

## 6. What I store in the memory graph

I use `neomemory` as a **living lab notebook** for this project:

* Entities for every concept that took me more than five minutes to figure out (e.g. `UID-1001`, `NEO4J_PLUGINS`, `server.jvm.additional`).
* Relations between them (`NEO4J_PLUGINS` → `renamed_from` → `NEO4JLABS_PLUGINS`).
* Observations that include the error message and the fix.

That way Copilot can recall the context later without me having to re‑explain it.
