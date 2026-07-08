# Plugins — what they do and the licensing caveats

The Neo4j image supports four community plugins that are commonly loaded together. None of them is required for a basic graph store, but each one unlocks a different category of work.

---

## `apoc` — Awesome Procedures On Cypher

The de‑facto standard utility library: ~400 procedures for JSON, CSV, paths, periodic jobs, refactoring, temporal handling, and more.

* **License:** Apache 2.0 (free for both Community and Enterprise).
* **When you need it:** Almost every non‑trivial project. `apoc.load.json`, `apoc.periodic.iterate`, `apoc.path.expandConfig` are used constantly.
* **Version coupling:** The APOC version must match your Neo4j major/minor version. Loading the wrong version at startup will throw a `RuntimeException`.

---

## `graph-data-science` — GDS

Adds graph‑algorithm procedures: PageRank, Louvain community detection, node similarity, embeddings, link prediction, …

* **License:** The plugin itself is open‑source, but **procedure‑level** licensing follows the Neo4j edition you're running:
  * **Community‑GDS procedures** are free.
  * **Enterprise‑only procedures** (some parallel ML models, certain streaming APIs) require a Neo4j Enterprise license.
* **macOS quirk:** Requires `server.jvm.additional=-Djol.skipHotspotSAAttach=true` in `neo4j.conf`. Without it the JVM fails to attach a HotSpot Serviceability Agent and the plugin refuses to load.
* **When you need it:** Anything involving centrality, community detection, embeddings, or graph ML.

---

## `genai` — GenAI Labs

Cypher procedures for calling external LLM APIs directly from Neo4j:

* `genai.chat.completion` — chat completions.
* `genai.embedding` — generate embeddings for text.
* `genai.vector.search` — vector search over stored embeddings.

It also ships helpers for prompt templating, token counting, and result post‑processing.

* **License:** Neo4j Labs — free for development and evaluation. For production you must comply with the underlying LLM provider’s terms (OpenAI, Azure OpenAI, Hugging Face, …).
* **When you need it:** You want to augment the graph with LLM‑generated text or embeddings without leaving Cypher (chat‑bots that walk the graph, automatic summarisation, …).

---

## `apoc-extended` — APOC Extended

A bundle of procedures that are only available with a Neo4j Enterprise license (advanced monitoring, backup, LDAP/SSO helpers, certain MongoDB/Elasticsearch integrations, …).

* **License:** The plugin source is Apache 2.0, but the procedures it exposes are gated by the Enterprise license.
* **Loading it on Community Edition** produces warnings and the procedures simply aren’t registered — it won’t break your startup, but it’s also useless.
* **When you need it:** Only if you have a valid Enterprise license and you actually need one of the enterprise‑only procedures.

---

## Recommended configuration

For a single‑user dev box on Community Edition:

```yaml
environment:
  - NEO4J_PLUGINS=["graph-data-science","genai","apoc"]
```

Add `apoc-extended` only when you have an Enterprise license.

---

## Verify the plugins are loaded

```cypher
CALL dbms.procedures() YIELD name
WHERE name STARTS WITH 'apoc.' OR name STARTS WITH 'gds.' OR name STARTS WITH 'genai.'
RETURN count(*) AS loadedProcedures;
```

A non‑zero count means the JARs were copied into `/plugins` and Neo4j registered their procedures.
