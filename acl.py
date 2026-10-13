"""ACL doc builder -- same shape as the old seeding script's acl.json, but with a wildcard
principal ("*") instead of a specific user, per this migration's requirement that every migrated
database end up with a principal-* ACL collection."""
from datetime import datetime, timezone

from bson import ObjectId

from config import TARGET_CLIENT_ID


def _now():
    return datetime.now(timezone.utc)


def build_acl_doc(resource_id, resource_type):
    """One ACL doc per migrated document. _id matches the resource's own _id (not prefixed with
    the resource type) -- still deterministic, so re-running the migration upserts the same doc
    instead of creating duplicates, and each resource only ever gets one ACL doc per destination
    database regardless of which collection it came from.

    _id is stored as a real bson.ObjectId, not a string -- confirmed every migrated collection's
    own _id (fabrix_v2, rules, bot, processors, etc.) is a genuine ObjectId, so the ACL doc's _id
    should match that type, not just look like one as a string."""
    now = _now()
    return {
        "_id": resource_id if isinstance(resource_id, ObjectId) else ObjectId(str(resource_id)),
        "identifier": f"{resource_type.lower()}/{resource_id}",
        "client_id": TARGET_CLIENT_ID,
        "slug": None,
        "hidden": False,
        "deleted_status": "N",
        "acl": [],
        "audit_data": {"create_user_id": None, "create_ts": now, "update_ts": now},
        "plugins": [],
        "miners": [],
        "tags": [],
        "principal": "*",
        "actions": ["read", "write"],
        "resource": {
            "identifier": str(resource_id),
            "hidden": False,
            "deleted_status": "N",
            "type": resource_type,
        },
    }


BLANKET_ENTITY_ACL_ID = ObjectId("000000000000000000000000")  # no real resource backs this row


def build_entity_blanket_acl_doc():
    """Hektor_entity has no real migrated resource docs (confirmed: the source `connections`
    database has zero Hektor/HC3 data), so it gets one blanket entity-level ACL doc instead of a
    per-resource loop. _id is a fixed, all-zero ObjectId sentinel -- kept as ObjectId (not a
    string) for consistency with every other row in this collection."""
    now = _now()
    return {
        "_id": BLANKET_ENTITY_ACL_ID,
        "identifier": "entity/*",
        "client_id": TARGET_CLIENT_ID,
        "slug": None,
        "hidden": False,
        "deleted_status": "N",
        "acl": [],
        "audit_data": {"create_user_id": None, "create_ts": now, "update_ts": now},
        "plugins": [],
        "miners": [],
        "tags": [],
        "principal": "*",
        "actions": ["read", "write"],
        "resource": {"identifier": "*", "hidden": False, "deleted_status": "N", "type": "entity"},
    }
