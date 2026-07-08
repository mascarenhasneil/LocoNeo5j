# Setup walk-through

> Step-by-step instructions for getting from a fresh macOS install to a running Neo4j container with the helper script.

---

## 1. Install the prerequisites

```bash
# Homebrew (if you don't already have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Colima + Docker CLI + Compose plugin
brew install colima docker docker-compose

# Start the lightweight Linux VM
colima start
# (optional) tune resources:
# colima start --cpu 4 --memory 4
```

Verify:

```bash
docker version            # Server should report linux/arm64
docker compose version    # should print a v2.x version number
```

---

## 2. Prepare the host folders

```bash
mkdir -p ~/neo4j/{data,logs,plugins,conf,import}
chown -R 1001:1001 ~/neo4j/{data,logs,plugins}
```

> UID `1001` is the `neo4j` user inside the official image. Pre-chowning avoids the `Folder mounted to ... is not writable from inside container` warnings.

---

## 3. Clone this repo and create your `.env`

```bash
git clone https://github.com/<you>/LocoNeo5j.git
cd LocoNeo5j
cp project/.env.example project/.env
# edit project/.env and set NEO4J_PASSWORD
```

The `.env` file is git-ignored — never commit it.

---

## 4. Copy the custom config into `~/neo4j/conf/`

The compose file mounts `~/neo4j/conf` into the container at `/conf`, and `NEO4J_CONF=/conf` tells the image to read it.

```bash
cp conf/neo4j.conf ~/neo4j/conf/neo4j.conf
```

---

## 5. (Optional) Drop any `.dump` files into the import folder

```bash
cp /path/to/your/*.dump ~/neo4j/import/
```

---

## 6. Start Neo4j

```bash
cd project
docker compose up -d
docker compose logs -f   # Ctrl-C to stop following
```

You should see `Started.` once Neo4j is ready.

Open `http://localhost:7474` in a browser and log in with `neo4j` / your password.

---

## 7. Use the helper script (optional but recommended)

```bash
cd /path/to/LocoNeo5j
python3 neo4j_manager.py
```

The script will:

1. Detect any running Neo4j container and offer to stop it.
2. List every `.dump` it finds in `~/neo4j/import/` and ask which one to load.
3. Run `neo4j-admin load` against the bind-mounts.
4. Start the long-running service.
5. Print the HTTP and Bolt connection info.
6. On Ctrl-C, optionally export the current database to a fresh `.dump` and tear the stack down.

### Non-interactive flags

```bash
python3 neo4j_manager.py --dump my-dump.dump      # load a specific dump
python3 neo4j_manager.py --empty                 # start with an empty DB
python3 neo3_manager.py --no-export --no-wait    # CI / scripted usage
```

---

## 8. Add an alias for the host (optional)

```bash
sudo nano /etc/hosts
# add: 127.0.0.1   neo4j
```

Now `http://neo4j:7474` works in the browser and `bolt://neo4j:7687` works in drivers.

---

## 9. Backup / migration

```bash
docker compose down
docker run --rm \
  -v neo4j_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/neo4j_data.tar.gz -C /data .
# repeat for neo4j_logs and neo4j_plugins if you care about them
```

Copy the `.tar.gz` to another machine, then:

```bash
docker volume create neo4j_data
docker run --rm \
  -v neo4j_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/neo4j_data.tar.gz -C /data
docker compose up -d
```

---

## 10. Tear it all down (without losing data)

```bash
cd project
docker compose down        # containers stop, bind-mounts persist
colima stop                # free RAM/CPU
```

To wipe everything (including the bind-mounts):

```bash
rm -rf ~/neo4j/{data,logs,plugins,conf,import}
colima delete              # remove the Linux VM
```
