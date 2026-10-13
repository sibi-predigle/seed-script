"""Builds standalone `connections` documents (destined for Hektor_entity.connections) from each
migrated bot's own embedded `configuration.sources[]`/`destinations[]` entries -- matching the
real schema confirmed against a sample export (pdb-entity-dev.connections.json): a connections
doc's top-level name/type/category/connection_config/connection_type are the exact same shape a
bot embeds inline, just promoted to a standalone, referenceable document.

HC3's bot already carries `connection_ref.reference_id` pointers on its source and destination
(ids 6a60e036b5e1889f1a06f8a2 / 69ccadf10ab6f287f499f4fb) -- confirmed these resolve to nothing
anywhere in this dev environment (checked pdb-precog-dev-qa.connections, which is empty, and the
unrelated pdb-entity-dev database, which has no matching docs either). Those exact ids are reused
here as the new connections docs' own _id, so the migration backs an existing dangling pointer
instead of creating an orphaned duplicate. The other 3 bots' source/destination entries have no
connection_ref at all; one is minted fresh and injected here, matching the convention every real
sample connection-bearing entry already follows."""
import copy
from datetime import datetime, timezone

from bson import ObjectId

IMAGE_URL_BY_TYPE = {
    "text": "./assets/icons/multiple-files.svg",
    "json": "./assets/icons/json.svg",
    "xml": "./assets/images/xml.png",
    "csv": "./assets/icons/csv.svg",
}


def _now():
    return datetime.now(timezone.utc)


def build_connection_doc(entry, client_id):
    """entry is one item from a bot's configuration.sources[]/destinations[] (a plain dict, as
    stored on the bot doc). Returns (connection_doc, connection_id) -- connection_id reuses
    entry's own connection_ref.reference_id when present, else is freshly minted."""
    existing_ref = (entry.get("connection_ref") or {}).get("reference_id")
    connection_id = ObjectId(existing_ref) if existing_ref else ObjectId()

    type_type = (entry.get("type") or {}).get("type")
    now = _now()
    doc = {
        "_id": connection_id,
        "client_id": client_id,
        "slug": None,
        "hidden": False,
        "deleted_status": "N",
        "acl": [],
        "audit_data": {
            "create_user_id": "0", "create_ts": now,
            "update_user_id": "0", "update_ts": now, "record_status": "A",
        },
        "name": entry.get("name"),
        "image_url": IMAGE_URL_BY_TYPE.get(type_type, "./assets/icons/multiple-files.svg"),
        "tags": [],
        "type": entry.get("type"),
        "category": entry.get("category"),
        "connection_config": entry.get("connection_config"),
        "plugins": [],
        "connection_type": entry.get("connection_type"),
    }
    return doc, connection_id


def with_connection_ref(entry, connection_id):
    """A copy of entry with connection_ref set -- added if missing, left pointing at the same
    id (unchanged) if it was already present."""
    entry = copy.deepcopy(entry)
    entry["connection_ref"] = {
        "hidden": False, "deleted_status": "N", "acl": [],
        "name": entry.get("name"), "reference_id": str(connection_id),
    }
    return entry


def build_connections_for_bot(bot_doc, client_id):
    """Processes one bot doc's sources[]/destinations[] in place (returns a new bot dict --
    does not mutate the input) and returns (patched_bot_doc, [connection_doc, ...]).
    Every source/destination entry ends up with a connection_ref; every connection_doc gets a
    deterministic _id so re-running this is idempotent."""
    bot_doc = copy.deepcopy(bot_doc)
    connection_docs = []

    config = bot_doc.get("configuration") or {}
    for key in ("sources", "destinations"):
        entries = config.get(key) or []
        patched_entries = []
        for entry in entries:
            doc, connection_id = build_connection_doc(entry, client_id)
            connection_docs.append(doc)
            patched_entries.append(with_connection_ref(entry, connection_id))
        config[key] = patched_entries

    return bot_doc, connection_docs
