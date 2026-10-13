"""Seeds the 3 pre-existing destination databases (Hektor_fabrix, Hektor_precog, Hektor_entity)
from the static JSON fixtures in data/. Does NOT connect to any source database -- everything it
writes was already exported into data/*.json ahead of time (see dump_fixtures.py), so this script
runs standalone in a new environment that has no access to the original live Rule_engine_main_1 /
pdb-precog-dev-qa databases.

Usage:
    python seed_client.py
    python seed_client.py --mongo-uri mongodb://other-host:27017
    python seed_client.py --dry-run
    python seed_client.py --resources-dir C:/Predigle/api-entity-precog/resources

Folder a bot's Local File Subscriber watches (replaces the value stored in the fixtures: the connection document
behind the bot's `local_file` connection runtime, and/or the source embedded in the bot, if it still has one). Pair each --bot-id with a --path, in order; repeat for more bots:
    python seed_client.py --bot-id 6ac6656b0717bfc9b1625932 --path /opt/home/predigle/inbox/bank_statements
    python seed_client.py --bot-id 6ac6656b0717bfc9b1625932 --path "C:\\Predigle\\hektor_inbox\\bank_statements" \\
                          --bot-id 6ac7a3ca10110026df8b33cd --path "C:\\Predigle\\hektor_inbox\\notice_of_transfer"
The path is stored exactly as typed. It must exist where the watcher runs (inside the container for Docker).

Bot/connection sources point at `resources/connections/...` (see resources_local.py). The files behind those
paths are bundled in this directory's `resources/` and copied into --resources-dir (the precog repo's
`resources/` folder) so the bots also run with GCP_CLOUD_BUCKET=False.
"""
import argparse
import filecmp
import shutil
from datetime import datetime, timezone
from pathlib import Path

from bson import json_util
from pymongo import MongoClient

from config import DEST_AGENT_DB, DEST_ENTITY_DB, DEST_FABRIX_DB, DEST_PRECOG_DB

DATA_DIR = Path(__file__).parent / "data"
BUNDLED_RESOURCES = Path(__file__).parent / "resources"
DEFAULT_RESOURCES_DIR = Path(__file__).resolve().parent.parent / "api-entity-precog" / "resources"


def load_json(filename):
    with open(DATA_DIR / filename, "r", encoding="utf-8") as f:
        return json_util.loads(f.read())


AUDIT_TS_FIELDS = ("create_ts", "update_ts")


def to_datetime(value):
    """String -> naive UTC datetime, or None if it is not a recognisable timestamp."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    text = text[:-1] + "+00:00" if text.endswith(("Z", "z")) else text
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def normalize_audit_timestamps(doc):
    """Turns string audit_data.create_ts/update_ts into real datetimes (in place); returns how many were changed.

    Django's DateTimeField cannot read a string, and /engine/bot/run/ then fails with
    "'str' object has no attribute 'utcoffset'". The shipped fixtures already hold real dates; this guard keeps a
    future dump or hand edit from seeding strings."""
    audit = doc.get("audit_data")
    changed = 0
    if isinstance(audit, dict):
        for key in AUDIT_TS_FIELDS:
            if isinstance(audit.get(key), str):
                parsed = to_datetime(audit[key])
                if parsed is not None:
                    audit[key] = parsed
                    changed += 1
    return changed


# (destination database -> destination collection -> fixture file)
DB_DUMPS = {
    DEST_FABRIX_DB: {
        "fabrix_v2": "fabrix_v2.json",
        "data_sources": "data_sources.json",
        "functions": "functions.json",
        "prompts": "prompts.json",
        "prompt_versions": "prompt_versions.json",
        "sections": "sections.json",
        "rule_blocks": "rule_blocks.json",
        "rules": "rules.json",
        "rule_conditions": "rule_conditions.json",
        "rule_actions": "rule_actions.json",
        "rule_types": "rule_types.json",
        "acl": "acl_fabrix.json",
    },
    DEST_PRECOG_DB: {
        "bot": "bot.json",
        "processors": "processors.json",
        "processor_types": "processor_types.json",
        "fnf_models": "fnf_models.json",
        "model_versions": "model_versions.json",
        "foundation_model": "foundation_model.json",
        "acl": "acl_precog.json",
    },
    DEST_ENTITY_DB: {
        "connections": "connections.json",
        "connection_runtime": "connection_runtime.json",
        "acl": "acl_entity.json",
    },
    DEST_AGENT_DB: {
        "agents": "agents.json",
        "state_types": "state_types.json",
        "acl": "acl_agent.json",
    },
}


LOCAL_FILE_TYPE = "local_file_adapter"


def is_local_file_source(source):
    adapter = ((source or {}).get("connection_type") or {}).get("adapter") or {}
    return (adapter.get("type") or {}).get("type") == LOCAL_FILE_TYPE


def pair_local_paths(bot_ids, paths):
    """{bot_id: path} from the repeated --bot-id / --path options (paired in order). Raises ValueError if unusable."""
    bot_ids, paths = bot_ids or [], paths or []
    if len(bot_ids) != len(paths):
        raise ValueError(f"--bot-id and --path must be given the same number of times (got {len(bot_ids)} and {len(paths)})")
    pairs = {}
    for bot_id, path in zip(bot_ids, paths):
        bot_id, path = bot_id.strip(), path.strip()
        if not bot_id or not path:
            raise ValueError("--bot-id and --path must not be empty")
        if bot_id in pairs and pairs[bot_id] != path:
            raise ValueError(f"bot {bot_id} was given two different paths")
        pairs[bot_id] = path
    return pairs


def runtime_connection_ids(runtime_docs, bot_id):
    """Connection ids behind the local_file runtimes of a bot (context.type bot, context.reference_id bot_id)."""
    ids = []
    for runtime in runtime_docs or []:
        context = runtime.get("context") or {}
        if (runtime.get("listener_type") == "local_file" and context.get("type") == "bot"
                and str(context.get("reference_id")) == bot_id):
            connection_id = str((runtime.get("config") or {}).get("connection_id") or "")
            if connection_id:
                ids.append(connection_id)
    return ids


def plan_local_paths(bot_docs, pairs, runtime_docs=None):
    """Checks every requested bot against the fixtures and returns {bot_id: {"path", "name", "connection_ids"}}.

    A bot's folder lives either in a Local File Subscriber source embedded in the bot (older setup; its
    connection_ref points at the connection) or in the connection of its `local_file` runtime (current setup).
    Raises ValueError (nothing is written yet) if a bot is unknown or has neither."""
    by_id = {str(b["_id"]): b for b in bot_docs}
    plan = {}
    for bot_id, path in pairs.items():
        bot = by_id.get(bot_id)
        if bot is None:
            raise ValueError(f"bot {bot_id} is not in data/bot.json; known bots: {', '.join(sorted(by_id))}")
        sources = [s for s in (bot.get("configuration") or {}).get("sources") or [] if is_local_file_source(s)]
        connection_ids = [str((s.get("connection_ref") or {}).get("reference_id") or "") for s in sources]
        connection_ids += runtime_connection_ids(runtime_docs, bot_id)
        if not sources and not connection_ids:
            raise ValueError(f"bot {bot_id} ({(bot.get('metadata') or {}).get('name')}) has no Local File Subscriber "
                             f"(neither a source on the bot nor a local_file connection runtime)")
        plan[bot_id] = {"path": path, "name": (bot.get("metadata") or {}).get("name") or bot_id,
                        "connection_ids": connection_ids}
    return plan


def apply_local_paths_to_bot(bot_doc, plan):
    """Sets config_value on the bot's local-file sources (in place). Returns [(source name, old, new)]."""
    entry = plan.get(str(bot_doc["_id"]))
    changes = []
    if entry:
        for source in (bot_doc.get("configuration") or {}).get("sources") or []:
            if is_local_file_source(source):
                config = source.setdefault("connection_config", {})
                changes.append((source.get("name"), config.get("config_value"), entry["path"]))
                config["config_value"] = entry["path"]
    return changes


def apply_local_paths_to_connection(connection_doc, plan):
    """Sets config_value on a connection document that backs one of the planned sources. Returns (old, new) or None."""
    for entry in plan.values():
        if str(connection_doc["_id"]) in entry["connection_ids"]:
            config = connection_doc.setdefault("connection_config", {})
            old, config["config_value"] = config.get("config_value"), entry["path"]
            return old, entry["path"]
    return None


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Seed client destination databases from data/*.json fixtures.")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--bot-id", "--bot_id", dest="bot_ids", action="append", metavar="BOT_ID",
                        help="bot whose Local File Subscriber folder to set (repeatable; pair with --path)")
    parser.add_argument("--path", dest="paths", action="append", metavar="FOLDER",
                        help="folder for the preceding/matching --bot-id: Linux (/opt/...) or Windows (C:\\...) path, "
                             "stored exactly as typed")
    parser.add_argument("--resources-dir", default=str(DEFAULT_RESOURCES_DIR),
                         help="precog `resources/` folder to copy the bundled source/mapping files into "
                              "(default: ../api-entity-precog/resources). Pass '' to skip.")
    parser.add_argument("--dry-run", action="store_true",
                         help="Print per-collection counts and 1-2 sample docs; write nothing.")
    return parser.parse_args(argv)


def copy_resources(dest_root, dry_run):
    """Copies bundled resources/** into dest_root, keeping relative paths. Unchanged files are skipped."""
    label = "[dry-run] " if dry_run else ""
    if not dest_root:
        print("\n[+] resources: skipped (--resources-dir '')")
        return
    dest_root = Path(dest_root)
    print(f"\n[+] {label}Copying bundled resources -> {dest_root}")
    for src in sorted(p for p in BUNDLED_RESOURCES.rglob("*") if p.is_file()):
        rel = src.relative_to(BUNDLED_RESOURCES)
        dest = dest_root / rel
        if dest.exists() and filecmp.cmp(src, dest, shallow=False):
            status = "unchanged"
        else:
            status = "copy"
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
        print(f"    - {label}{status}: {rel.as_posix()}")


def main(argv=None):
    args = parse_args(argv)
    label = "[dry-run] " if args.dry_run else ""

    # Validate the requested folder overrides against the fixtures BEFORE connecting or writing anything.
    try:
        plan = plan_local_paths(load_json("bot.json"), pair_local_paths(args.bot_ids, args.paths),
                                load_json("connection_runtime.json"))
    except ValueError as exc:
        print(f"[ERROR] {exc}")
        return 2
    client = MongoClient(args.mongo_uri) if not args.dry_run else None

    total = 0
    for db_name, collections in DB_DUMPS.items():
        db = client[db_name] if client is not None else None
        print(f"\n[+] {label}Seeding database: '{db_name}'")
        for coll_name, filename in collections.items():
            docs = load_json(filename)
            if plan and coll_name == "bot":
                for doc in docs:
                    for source_name, old, new in apply_local_paths_to_bot(doc, plan):
                        print(f"    > {label}bot {doc['_id']} source {source_name!r}: folder {old!r} -> {new!r}")
            elif plan and coll_name == "connections":
                for doc in docs:
                    change = apply_local_paths_to_connection(doc, plan)
                    if change:
                        print(f"    > {label}connection {doc['_id']} ({doc.get('name')}): folder {change[0]!r} -> {change[1]!r}")
            converted = sum(normalize_audit_timestamps(d) for d in docs)
            if converted:
                print(f"    ! {coll_name}: converted {converted} string audit timestamp(s) to dates")
            if args.dry_run:
                for sample in docs[:2]:
                    print(f"        sample _id={sample['_id']}")
            else:
                coll = db[coll_name]
                for doc in docs:
                    coll.replace_one({"_id": doc["_id"]}, doc, upsert=True)
            print(f"    - {label}{coll_name} <- data/{filename}: {len(docs)} docs")
            total += len(docs)

    copy_resources(args.resources_dir, args.dry_run)

    print(f"\n[OK] {label}Seeded {total} documents across {len(DB_DUMPS)} databases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
