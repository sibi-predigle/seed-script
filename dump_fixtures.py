"""Dev-only, one-time tool: queries the LIVE source databases (Rule_engine_main_1,
pdb-precog-dev-qa) and writes the data/*.json fixtures that seed_client.py ships with and loads.

This is NOT what the target/new environment runs. seed_client.py never connects to a source
database -- it only reads the static JSON files already sitting in data/. Run this script again,
from a machine that *does* have network access to those live source databases, only if the scope
in config.py (FABRIX_IDS, BOT_IDS, etc.) ever changes and the fixtures need regenerating. See
README.md for the full id-derivation methodology.

Usage: python dump_fixtures.py [--mongo-uri mongodb://localhost:27017]
"""
import argparse
import os
from datetime import datetime
from pathlib import Path

from bson import ObjectId, json_util

from acl import build_acl_doc, build_entity_blanket_acl_doc
from config import DEST_ENTITY_DB, DEST_FABRIX_DB, DEST_PRECOG_DB, FABRIX_ID_REMAP, MIGRATIONS, MODEL_DOC_IDS, MODEL_SOURCE_DB, PROCESSOR_MODEL_REFS, TARGET_CLIENT_ID
from connections import build_connections_for_bot
import local_sub
from resources_local import localize

DATA_DIR = Path(__file__).parent / "data"

# Fixture filename for each (dest_db, dest_coll) pair migrated below.
FIXTURE_FILENAMES = {
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
    "bot": "bot.json",
    "processors": "processors.json",
    "processor_types": "processor_types.json",
}

# Model docs copied verbatim from the dev cluster (read-only) -> precog database.
MODEL_FIXTURES = {
    "fnf_models": ("fnf_models.json", "FNFModel"),
    "model_versions": ("model_versions.json", "ModelVersion"),
    "foundation_model": ("foundation_model.json", "FoundationModel"),
}

# Which destination database's acl fixture each dest_coll's ACL docs belong to.
ACL_FIXTURE_BY_DEST_DB = {
    DEST_FABRIX_DB: "acl_fabrix.json",
    DEST_PRECOG_DB: "acl_precog.json",
}


def normalize_audit_timestamps(doc):
    """Some source docs hold audit_data.*_ts as 'YYYY-MM-DD HH:MM:SS.ffffff' strings (written by a
    script, not the app). Django's DateTimeField then fails on read ("'str' object has no attribute
    'utcoffset'") and /engine/bot/run/ returns a 500, so store them as real datetimes."""
    audit = doc.get("audit_data")
    if isinstance(audit, dict):
        for key, value in audit.items():
            if key.endswith("_ts") and isinstance(value, str):
                audit[key] = datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def write_json(filename, docs):
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        f.write(json_util.dumps(docs, indent=2))
    print(f"wrote data/{filename}: {len(docs)} docs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017")
    parser.add_argument("--dev-uri", default=os.environ.get("DEV_MONGO_URI"),
                        help="Dev cluster URI, used READ-ONLY (find_one) to refresh the model fixtures "
                             "(fnf_models, model_versions, foundation_model). Without it those "
                             "fixtures are left as they are.")
    args = parser.parse_args()

    from pymongo import MongoClient

    client = MongoClient(args.mongo_uri)

    acl_docs_by_dest_db = {DEST_FABRIX_DB: [], DEST_PRECOG_DB: [], DEST_ENTITY_DB: []}
    connection_docs = []

    for src_db, src_coll, dest_db, dest_coll, query, acl_type in MIGRATIONS:
        query = {**query, "deleted_status": {"$ne": "Y"}}
        docs = list(client[src_db][src_coll].find(query))
        for doc in docs:
            doc["client_id"] = TARGET_CLIENT_ID
            normalize_audit_timestamps(doc)

        if dest_coll == "processors":
            for doc in docs:
                ref = (doc.get("fabrix") or {}).get("reference_id")
                if ref in FABRIX_ID_REMAP:
                    doc["fabrix"]["reference_id"], doc["fabrix"]["name"] = FABRIX_ID_REMAP[ref]
                if str(doc["_id"]) in PROCESSOR_MODEL_REFS:
                    doc["model"] = PROCESSOR_MODEL_REFS[str(doc["_id"])]

        if dest_coll == "bot":
            # Every bot's sources[]/destinations[] gets a real, standalone connections doc
            # (Hektor_entity.connections) and a connection_ref pointing at it -- backing HC3's
            # already-dangling connection_ref ids, and minting fresh ones for the other bots.
            patched_docs = []
            for doc in docs:
                # bucket URLs -> `resources/...` so the bot also runs with GCP_CLOUD_BUCKET=False
                doc = localize(doc)
                patched_doc, docs_for_this_bot = build_connections_for_bot(doc, TARGET_CLIENT_ID)
                patched_docs.append(patched_doc)
                connection_docs.extend(docs_for_this_bot)
            docs = patched_docs

        write_json(FIXTURE_FILENAMES[dest_coll], docs)

        acl_docs_by_dest_db[dest_db].extend(build_acl_doc(doc["_id"], acl_type) for doc in docs)

    if args.dev_uri:
        dev = MongoClient(args.dev_uri)
        for coll, (filename, acl_type) in MODEL_FIXTURES.items():
            doc = dev[MODEL_SOURCE_DB][coll].find_one({"_id": ObjectId(MODEL_DOC_IDS[coll])})
            if doc is None:
                raise SystemExit(f"{MODEL_SOURCE_DB}.{coll} {MODEL_DOC_IDS[coll]} not found on the dev cluster")
            write_json(filename, [doc])
            acl_docs_by_dest_db[DEST_PRECOG_DB].append(build_acl_doc(doc["_id"], acl_type))
    else:
        print("No --dev-uri/DEV_MONGO_URI: model fixtures left unchanged (their ACL docs are kept too).")
        for coll, (filename, acl_type) in MODEL_FIXTURES.items():
            for doc in json_util.loads((DATA_DIR / filename).read_text(encoding="utf-8")):
                acl_docs_by_dest_db[DEST_PRECOG_DB].append(build_acl_doc(doc["_id"], acl_type))

    write_json("connections.json", connection_docs)
    acl_docs_by_dest_db[DEST_ENTITY_DB].extend(
        build_acl_doc(doc["_id"], "Connection") for doc in connection_docs
    )

    for dest_db, filename in ACL_FIXTURE_BY_DEST_DB.items():
        write_json(filename, acl_docs_by_dest_db[dest_db])

    acl_docs_by_dest_db[DEST_ENTITY_DB].append(build_entity_blanket_acl_doc())
    write_json("acl_entity.json", acl_docs_by_dest_db[DEST_ENTITY_DB])

    # The Local File Subscription (1 connection + 2 runtimes, nothing on the bot) is authored, not dumped:
    # re-apply it so regenerating the fixtures keeps it.
    for line in local_sub.apply_to_fixtures(DATA_DIR):
        print(line)

    print(f"\nFixtures written to {DATA_DIR} -- commit/ship this directory alongside seed_client.py.")


if __name__ == "__main__":
    main()
