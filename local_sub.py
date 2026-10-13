"""Local File Subscription seed: ONE connection + TWO connection runtimes, nothing on any bot.

api-connections (`manage.py run_local_file_sub`) reads these:
  connection          "Hektor - Local File Sub (Bank Statements)": type local_file_adapter, the watched folder in
                      connection_config.config_value
  runtime A (PAUSED)  context {type: bot,   reference_id: <Statement bot id>}   -> would trigger the Precog bot (switched off)
  runtime B (RUNNING) context {type: agent, reference_id: <Hektor Agent id>}    -> same connection; triggers the agent copied
                      into Hektor_agent_4 (id 6acdd6c63d578a20bff2713a). Set the statuses the other way round to feed the bot instead.

Runtime names follow api-connections' own convention "{type}:{reference_id}:{source_type}:{connection_id}" with
source_type = the connection's type ("local_file_adapter").

`apply_to_fixtures(data_dir)` is idempotent: it upserts those documents into data/connections.json,
data/connection_runtime.json and data/acl_entity.json, and removes the OLD bot-embedded subscriber of the Statement
bot (its `configuration.sources` entry, its connection document and that connection's ACL entry), because the
subscription now relies on connections only.

    python local_sub.py                 # apply to ./data
    python local_sub.py --dry-run       # print what would change
    python local_sub.py --folder /opt/home/predigle/inbox/bank_statements
"""
import argparse
import copy
from datetime import datetime
from pathlib import Path

from bson import ObjectId, json_util

from config import TARGET_CLIENT_ID

BOT_ID = "6ac6656b0717bfc9b1625932"                 # Hektor Bank Loan Statement Extraction (Rule Engine)
AGENT_ID = "6acdd6c63d578a20bff2713a"                # "Hektor Agent" (Hektor_agent_4.agents, copied from pdb-agents)
DEFAULT_FOLDER = r"C:\Predigle\hektor_inbox\bank_statements"

CONNECTION_ID = "6ad0000000000000000f1e01"
BOT_RUNTIME_ID = "6ad0000000000000000f1e02"
AGENT_RUNTIME_ID = "6ad0000000000000000f1e03"
CONNECTION_NAME = "Hektor - Local File Sub (Bank Statements)"
SOURCE_TYPE = "local_file_adapter"                   # connection `type.type`; also the 3rd part of the runtime name

OLD_BOT_CONNECTION_ID = "6acc9594d270343c5d96569c"   # the bot-embedded subscriber's connection, replaced by the above
STAMP = datetime(2026, 10, 12, 0, 0, 0)              # fixed so regenerating gives identical files; a real datetime, never a string


def audit():
    return {"create_user_id": "0", "create_ts": STAMP, "update_user_id": "0", "update_ts": STAMP, "record_status": "A"}


def runtime_name(kind, reference_id):
    return f"{kind}:{reference_id}:{SOURCE_TYPE}:{CONNECTION_ID}"


def build_connection(folder=DEFAULT_FOLDER):
    adapter = {
        "identifier": "90cb21c9-afac-4b67-b922-4bf3c14f8cf2", "hidden": False, "deleted_status": "N", "acl": [], "tags": [],
        "name": "Local File Adapter", "type": {"name": "Local File Adapter", "type": "local_file_adapter"},
        "category": "source", "status": "active",
        "module_name": "engine.adapters.file_adapter.file_adapter", "class_name": "FileHandler",
    }
    parser = {
        "identifier": "83f59571-8184-470a-a0a4-4f60df5a558a", "hidden": False, "deleted_status": "N", "acl": [], "tags": [],
        "name": "File Parser", "type": {"name": "File Parser", "type": "file_parser"},
        "category": "source/destination", "status": "active",
        "module_name": "engine.framework.parsers.file", "class_name": "FileParser",
    }
    return {
        "_id": ObjectId(CONNECTION_ID), "client_id": TARGET_CLIENT_ID, "slug": None, "hidden": False,
        "deleted_status": "N", "acl": [], "audit_data": audit(), "name": CONNECTION_NAME,
        "image_url": "./assets/icons/multiple-files.svg", "tags": [],
        "type": {"name": "Local File Subscriber", "type": SOURCE_TYPE}, "category": "source",
        "connection_config": {
            "hidden": False, "deleted_status": "N", "acl": [], "tags": [], "category": "", "status": "",
            "parser_id": "", "config_type": "", "config_value": folder, "options": None, "config_options": None,
            "auth": {"hidden": False, "deleted_status": "N", "acl": [], "tags": [], "auth_type": "NO_AUTH", "body_type": "json"},
        },
        "plugins": [],
        "connection_type": {
            "hidden": False, "deleted_status": "N", "acl": [], "tags": [],
            "type": {"name": "Local File Adapter", "type": "local_file_adpater"},   # historical spelling, as in the other local-file connections
            "category": "sheets", "status": "", "adapter": adapter, "parser": parser,
        },
    }


def build_connection_acl():
    return {
        "_id": ObjectId(CONNECTION_ID), "identifier": f"connection/{CONNECTION_ID}", "client_id": TARGET_CLIENT_ID,
        "slug": None, "hidden": False, "deleted_status": "N", "acl": [],
        "audit_data": {"create_user_id": None, "create_ts": STAMP, "update_ts": STAMP},
        "plugins": [], "miners": [], "tags": [], "principal": "*", "actions": ["read", "write"],
        "resource": {"identifier": CONNECTION_ID, "hidden": False, "deleted_status": "N", "type": "Connection"},
    }


def build_runtime(_id, kind, reference_id, status):
    name = runtime_name(kind, reference_id)
    return {
        "_id": ObjectId(_id), "client_id": TARGET_CLIENT_ID, "slug": None, "hidden": False, "deleted_status": "N",
        "acl": [], "audit_data": audit(), "tags": [], "name": name,
        "context": {"reference_id": reference_id, "type": kind, "name": name},
        "listener_type": "local_file", "source_type": "folder", "source_value": "folder",
        "status": status,
        "config": {"connection_id": CONNECTION_ID, "file_param_key": None},
        "runtime": {}, "heartbeat": {}, "stats": {"processed": 0}, "error": {},
    }


def build_runtimes():
    return [
        build_runtime(BOT_RUNTIME_ID, "bot", BOT_ID, "PAUSED"),
        build_runtime(AGENT_RUNTIME_ID, "agent", AGENT_ID, "RUNNING"),
    ]


# --------------------------------------------------------------------------- fixtures
def _load(path):
    return json_util.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else []


def _upsert(docs, new_docs):
    ids = {d["_id"] for d in new_docs}
    return [d for d in docs if d["_id"] not in ids] + new_docs


def _is_local_file_source(source):
    adapter = ((source or {}).get("connection_type") or {}).get("adapter") or {}
    return (adapter.get("type") or {}).get("type") == "local_file_adapter"


def apply_to_fixtures(data_dir, folder=DEFAULT_FOLDER, dry_run=False):
    """Returns a list of human-readable change lines; writes the files unless dry_run."""
    data_dir = Path(data_dir)
    changes, out = [], {}

    connections = _load(data_dir / "connections.json")
    before = len(connections)
    connections = [c for c in connections if str(c["_id"]) != OLD_BOT_CONNECTION_ID]
    if len(connections) != before:
        changes.append(f"connections.json: removed the old bot-embedded connection {OLD_BOT_CONNECTION_ID}")
    existing = next((c for c in connections if str(c["_id"]) == CONNECTION_ID), None)
    keep_folder = ((existing or {}).get("connection_config") or {}).get("config_value")
    connections = _upsert(connections, [build_connection(keep_folder or folder)])
    changes.append(f"connections.json: upsert {CONNECTION_ID} ({CONNECTION_NAME}), folder {keep_folder or folder!r}")
    out["connections.json"] = connections

    acl = _load(data_dir / "acl_entity.json")
    acl = [a for a in acl if str(a["_id"]) != OLD_BOT_CONNECTION_ID]
    acl = _upsert(acl, [build_connection_acl()])
    changes.append("acl_entity.json: upsert the connection's ACL entry; removed the old connection's")
    out["acl_entity.json"] = acl

    runtimes = _load(data_dir / "connection_runtime.json")
    runtimes = _upsert(runtimes, build_runtimes())
    changes.append(f"connection_runtime.json: upsert {len(build_runtimes())} runtimes "
                   f"(bot {BOT_ID} PAUSED, agent {AGENT_ID} RUNNING)")
    out["connection_runtime.json"] = runtimes

    bots = _load(data_dir / "bot.json")
    for bot in bots:
        if str(bot["_id"]) == BOT_ID:
            sources = (bot.get("configuration") or {}).get("sources") or []
            kept = [s for s in sources if not _is_local_file_source(s)]
            if len(kept) != len(sources):
                bot["configuration"]["sources"] = kept
                changes.append(f"bot.json: removed the bot-embedded Local File Subscriber source from {BOT_ID}")
    out["bot.json"] = bots

    if not dry_run:
        for name, docs in out.items():
            (data_dir / name).write_text(json_util.dumps(docs, indent=2), encoding="utf-8")
    return changes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", default=str(Path(__file__).parent / "data"))
    ap.add_argument("--folder", default=DEFAULT_FOLDER)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    for line in apply_to_fixtures(args.data_dir, args.folder, args.dry_run):
        print(("[dry-run] " if args.dry_run else "") + line)


if __name__ == "__main__":
    main()
