#!/usr/bin/env python3
"""
neo4j_manager.py — one-click import / export for a single Neo4j instance.

Workflow:
  1. Detect any running Neo4j container and offer to stop it.
  2. List every *.dump file in ~/neo4j/import/ and ask which one to load
     (or start with an empty database).
  3. Run `neo4j-admin load` in a throw-away container that shares the
     same bind-mounts / config as the long-running service.
  4. Bring the long-running service up with `docker compose up -d`.
  5. Print HTTP and Bolt connection info.
  6. Wait for Ctrl-C, then optionally export the current database to a
     fresh *.dump file and tear the stack down.

Usage:
    python3 neo4j_manager.py                 # interactive picker
    python3 neo4j_manager.py --dump FILE     # non-interactive: load FILE
    python3 neo4j_manager.py --empty         # start with an empty DB
    python3 neo4j_manager.py --no-export     # skip the export prompt
    python3 neo4j_manager.py --no-wait       # don't block for Ctrl-C
"""

import argparse
import os
import pathlib
import shlex
import subprocess
import sys
import time
from typing import Optional

# ---------------------------------------------------------------------------
# USER-CONFIG — adjust only if you moved the project
# ---------------------------------------------------------------------------
BASE_DIR = pathlib.Path(__file__).resolve().parent
DUMP_DIR = pathlib.Path(os.path.expanduser("~/neo4j/import"))
COMPOSE_FILE = BASE_DIR / "project" / "docker-compose.yml"
CONFIG_FILE = BASE_DIR / "conf" / "neo4j.conf"

VOL_DATA = "neo4j_data"
VOL_LOGS = "neo4j_logs"
VOL_PLUG = "neo4j_plugins"

NEO4J_IMAGE = "neo4j:latest"  # matches project/docker-compose.yml
# ---------------------------------------------------------------------------


def run(cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command, printing it first."""
    print(f"\n:> {cmd}")
    return subprocess.run(shlex.split(cmd), check=check, text=True)


def container_running(service: str = "neo4j") -> bool:
    """Return True if the compose service is currently up."""
    result = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "ps", "-q", service],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())


def stop_stack() -> None:
    """Bring the compose stack down (containers stop, volumes stay)."""
    if container_running():
        print("\n→ Stopping Neo4j stack.")
        run(f"docker compose -f {COMPOSE_FILE} down")
    else:
        print("\n· Neo4j stack is already stopped.")


def load_dump(dump_name: str) -> None:
    """Import a dump file into the bind-mounts (force overwrite)."""
    dump_path = DUMP_DIR / dump_name
    if not dump_path.is_file():
        sys.exit(f"❌ Dump not found: {dump_path}")

    print(f"\n→ Loading dump {dump_name} into the volumes.")
    cmd = (
        f"docker run --rm "
        f"-v {VOL_DATA}:/data "
        f"-v {VOL_LOGS}:/logs "
        f"-v {VOL_PLUG}:/plugins "
        f"-v {DUMP_DIR}:/import:ro "
        f"-v {CONFIG_FILE}:/var/lib/neo4j/conf/neo4j.conf:ro "
        f"{NEO4J_IMAGE} "
        f"neo4j-admin load "
        f"--from=/import/{dump_name} "
        f"--database=neo4j "
        f"--force"
    )
    run(cmd)
    print("✓ Load finished.")


def export_dump(tag: Optional[str] = None) -> pathlib.Path:
    """Export the current database to a dump file in DUMP_DIR."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    tag = tag or "export"
    dump_name = f"{tag}_{ts}.dump"
    dump_path = DUMP_DIR / dump_name

    print(f"\n→ Exporting current database to {dump_name}")
    cmd = (
        f"docker run --rm "
        f"-v {VOL_DATA}:/data "
        f"-v {VOL_LOGS}:/logs "
        f"-v {VOL_PLUG}:/plugins "
        f"-v {DUMP_DIR}:/dump "
        f"{NEO4J_IMAGE} "
        f"neo4j-admin dump "
        f"--to=/dump/{dump_name} "
        f"--database=neo4j"
    )
    run(cmd)
    print(f"✓ Dump written: {dump_path}")
    return dump_path


def start_stack() -> None:
    """Bring up the long-running Neo4j service."""
    print("\n→ Starting Neo4j service")
    run(f"docker compose -f {COMPOSE_FILE} up -d")
    time.sleep(2)
    print("✓ Neo4j is up.")


def show_connection_info() -> None:
    """Print the host ports that the compose file maps."""
    http = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "port", "neo4j", "7474"],
        capture_output=True, text=True,
    ).stdout.strip()
    bolt = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "port", "neo4j", "7687"],
        capture_output=True, text=True,
    ).stdout.strip()
    print("\n· Connection info:")
    print(f"    HTTP : http://{http}")
    print(f"    Bolt : bolt://{bolt}")
    print("    (use the Neo4j Browser or any Bolt driver)")


def interactive_pick() -> Optional[str]:
    """Ask the user to pick a dump file or start empty."""
    DUMP_DIR.mkdir(parents=True, exist_ok=True)
    dumps = sorted(p.name for p in DUMP_DIR.glob("*.dump"))

    if dumps:
        print("\n· Available dump files in", DUMP_DIR)
        for i, d in enumerate(dumps, start=1):
            print(f"  {i}) {d}")
        print("  n) Start with an empty database (no dump)")
        print("  q) Quit")
    else:
        print(f"\n· No .dump files found in {DUMP_DIR}.")
        print("  n) Start with an empty database")
        print("  q) Quit")

    while True:
        choice = input("\nSelect a number, 'n' for empty, or 'q' to quit: ").strip().lower()
        if choice == "q":
            sys.exit(0)
        if choice == "n":
            return None  # marker for "empty"
        if choice.isdigit() and 1 <= int(choice) <= len(dumps):
            return dumps[int(choice) - 1]
        print("Invalid selection — try again.")


def wait_for_user() -> None:
    """Block until the user presses Ctrl-C or types 'stop'."""
    print("\n· Press Ctrl-C (or type 'stop' and hit Enter) when you are done.\n")
    try:
        while True:
            line = input()
            if line.strip().lower() == "stop":
                break
    except KeyboardInterrupt:
        pass


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--dump", help="load this dump file non-interactively, then start")
    p.add_argument("--empty", action="store_true", help="start with an empty database")
    p.add_argument("--no-export", action="store_true", help="skip the export prompt on exit")
    p.add_argument("--no-wait", action="store_true", help="don't block for Ctrl-C")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # 1. Decide what to do with any currently-running stack
    if container_running():
        print("\n· A Neo4j instance is already running.")
        ans = input("Do you want to stop it first? (y/N): ").strip().lower()
        if ans == "y":
            stop_stack()
        else:
            print("Keeping the running instance — you can still work with it.")
            show_connection_info()
            if not args.no_wait:
                wait_for_user()
            if not args.no_export:
                if input("\nExport the current database to a dump file? (y/N): ").strip().lower() == "y":
                    export_dump()
            stop_stack()
            return

    # 2. Pick a dump to load (or start empty)
    if args.dump:
        dump_to_load = args.dump
    elif args.empty:
        dump_to_load = None
    else:
        dump_to_load = interactive_pick()

    if dump_to_load:
        stop_stack()
        load_dump(dump_to_load)

    # 3. Bring up the long-running service
    start_stack()
    show_connection_info()

    # 4. Wait for the user to finish
    if not args.no_wait:
        wait_for_user()

    # 5. Optional export before tearing down
    if not args.no_export:
        if input("\nExport the current database to a dump file? (y/N): ").strip().lower() == "y":
            export_dump()

    # 6. Bring the stack down
    print("\n→ Shutting down…")
    stop_stack()
    print("✓ All done. The bind-mounts persist for the next run.")


if __name__ == "__main__":
    main()
