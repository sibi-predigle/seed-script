"""Declarative migration scope for seed_client.py.

Every id list below was derived once, by direct inspection of the live source databases
(`Rule_engine_main_1` for fabrix, `pdb-precog-dev-qa` for precog) against `mongodb://localhost:27017`.
See README.md for the exact derivation method for each list -- re-run that method rather than
guessing if this ever needs to cover a different bundle or client.
"""
from bson import ObjectId

TARGET_CLIENT_ID = "691ad32be2653616d96af2d5"  # the id every migrated document gets retagged to

# Pre-existing, already-provisioned destination databases -- these literal names are given/external,
# not a naming choice; every other identifier in this script stays client-agnostic.
DEST_FABRIX_DB = "pdb-pi-dev"
DEST_PRECOG_DB = "pdb-precog-dev"
DEST_ENTITY_DB = "pdb-entity-dev"
# The agents database: seeded from data/agents.json, state_types.json, acl_agent.json (static fixtures; no executions).
DEST_AGENT_DB = "pdb-agent-dev"

# The Postman-covered bots/processors (postman/hektor-hc3-botruns.postman_collection.json) --
# precog-side scope stays exactly these, since no other Hektor fabrix has a matching bot/processor.
# "Phi Redaction Precog" is the one exception: a standalone bot with no fabrix at all (OCR +
# Gemini-based PHI detection/redaction, engine.processors.anonymizer.phi_redaction), dumped
# verbatim from the live pdb-precog-dev-qa export the user provided (Desktop/Hecktor/phi_redaction) --
# client_id intentionally left as its own (64c48dc0eb5ba14e7588cbe6), NOT retagged to Hektor's,
# per explicit instruction to migrate it exactly as given.
BOT_IDS = [
    "6a60e094d3b42957dd173880",  # HC3 Fiserv DNA Masking
    # "6ac615f4e2e56d504687a2f9",  # Hektor Bank Statement Document -- uses fabrix 6ac5e5f0c1ffbf41d82595e1, commented out below
    "6ac6656b0717bfc9b1625932",  # Bank Loan Statement Extraction
    "6ac7a3ca10110026df8b33cd",  # Notice of Transfer Letter Masking
    "6aa95dea43949b401138905c",  # Phi Redaction Precog
]
PROCESSOR_IDS = [
    "6a60e06d3ed84624e4a7cbe9",  # HC3 Fiserv DNA Masking
    # "6ac615e8e2e56d504687a2f7",  # Hektor Bank Statement Document -- uses fabrix 6ac5e5f0c1ffbf41d82595e1, commented out below
    "6ac6656b0717bfc9b1625930",  # Bank Loan Statement Extraction
    "6ac7a3ba10110026df8b33cb",  # Notice of Transfer Letter Masking
    "6aa93548e04eef122a9b4407",  # PHI Redaction Processor
]

# Each in-scope processor's own `type.reference_id` field, pointing into `processor_types`.
# HC3 Fiserv DNA Masking -> "pi/data/process/masking"; the other 2 (both
# RuleEngineTransformationProcessor) -> "pi/data/process/transformation" -- 2 distinct types shared
# across the 3 processors, confirmed by reading all 3 processor docs' `type.reference_id`.
# PHI Redaction Processor has no entry here -- its own `type` field (as exported from the source
# system) carries no `reference_id` at all, just a bare display name; nothing to migrate for it,
# and not fabricated here since the user asked to migrate exactly what was provided, no more.
PROCESSOR_TYPE_IDS = [
    "674deade8e543636b4052137",  # pi/data/process/masking
    "691b375c509165efb68b7e49",  # pi/data/process/transformation
]

# The 15 original live Hektor fabrixes + the 1 real HC3 one (excludes a junk "test" HC3 doc,
# confirmed via {"client_id": {"$in": [HEKTOR, HC3]}, "deleted_status": {"$ne": "Y"}} against
# fabrix_v2) + the new "Notice of Transfer Letter Masking" fabrix authored this session (17 total).
#
# Only 4 of these 17 are actually "used" -- referenced by one of the 5 in-scope PROCESSOR_IDS'
# own `fabrix.reference_id` (confirmed by reading every in-scope processor doc). The other 13
# have no bot/processor pointing at them at all in this scope, so they're commented out below
# (kept, not removed, in case a future bot/processor for one of them gets added to PROCESSOR_IDS).
FABRIX_IDS = [
    # "6ac5e5f0c1ffbf41d82595e1",  # Hektor Bank Statement Document -- fragments weren't showing up in the UI after migration; commented out along with its bot/processor until that's root-caused
    "6acca142546eee5cf25270f6",  # Hektor Bank Statement Extraction (rule-engine v2 migration) -- used by "Bank Loan Statement Extraction PS" processor
    # "6ac5e5f6c1ffbf41d8259641",  # Hektor LAS330 -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac5e5fbc1ffbf41d825967f",  # Hektor ls300-pspdoc -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac5e60ec1ffbf41d82596c9",  # Hektor Bank Letter -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac6598c6a96f8432eca0a7a",  # Hektor Multi Record Pipe Delimited File Mapping -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac659916a96f8432eca0acb",  # Hektor FLS Mapping File -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac6599a6a96f8432eca0b62",  # Hektor Nested JSON File -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac6599f6a96f8432eca0bb9",  # Hektor DTD Validated File -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac659a86a96f8432eca0c52",  # Hektor XSD Validated File -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac659e46a96f8432eca0ff1",  # Hektor Single Record Pipe Delimited File -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac659e56a96f8432eca1004",  # Hektor Customer Data CSV -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac659e66a96f8432eca101d",  # Hektor FLS Validated XML File -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac659f16a96f8432eca10b4",  # Hektor Patient Data Transformer -- no processor in PROCESSOR_IDS references this fabrix
    # "6ac659f16a96f8432eca10bf",  # Hektor Monthly Transaction Transformer -- no processor in PROCESSOR_IDS references this fabrix
    "6ac659f96a96f8432eca10d6",  # HC3 Fiserv DNA Masking -- used by "Masking processor hc3" processor
    "6ac7a348c39023e81a5490a9",  # Notice of Transfer Letter Masking (new RegexBlockAdapter bot) -- used by "Notice of Transfer Letter Masking Processor"
]

# One per fabrix above, read from each fabrix_v2 doc's own data_source.reference_id field.
# Only 16 entries for 17 fabrixes: "Hektor Customer Data CSV" has no data_source field set
# (confirmed, not an omission here).
DATASOURCE_IDS = [
    "692da910e032bfaa1e13c41c",  # Hektor Bank Statement Document -> DS - Bank Statement
    "6acca140546eee5cf25270f4",  # Hektor Bank Statement Extraction -> DS - Hektor Bank Statement Extraction
    "69d39bc929f555b150e57818",  # Hektor LAS330 -> DS - LAS3300 PDSPDOC Loan Billing
    "69ddf8ee45b1e7b4df491b9c",  # Hektor ls300-pspdoc -> DS - LAS3300 PDSPDOC Loan Billing
    "692da1a949e5e2a4f4400938",  # Hektor Bank Letter -> DS - Bank Letter
    "691b0dfcad2662ce4f0312fa",  # Hektor Multi Record Pipe Delimited File Mapping
    "691b0e39ad2662ce4f031304",  # Hektor FLS Mapping File
    "691b0e4bad2662ce4f031309",  # Hektor Nested JSON File
    "691b0f18ad2662ce4f03130e",  # Hektor DTD Validated File
    "691b0f2cad2662ce4f031313",  # Hektor XSD Validated File
    "691b3c1bc8028fbfa9048fb5",  # Hektor Single Record Pipe Delimited File
    "691b3ce8c8028fbfa9048fba",  # Hektor Patient Data Transformer -> Customer CSV Input File
    "691b4104c8028fbfa9048fc4",  # Hektor FLS Validated XML File
    "691cca789a73eb39f4ccfb1a",  # Hektor Monthly Transaction Transformer
    "6ac65fc56a96f8432eca10f1",  # HC3 Fiserv DNA Masking -> HC3 Fiserv DNA Masking Fields
    "6ac7a348c39023e81a5490a7",  # Notice of Transfer Letter Masking -> Notice of Transfer Letter Fields
]

# From scanning every in-scope `rules` doc's actions[] for slug == "custom_function" and reading
# action.params.function_ref.reference_id.
FUNCTION_IDS = [
    "691dcb0f6de2706efbf6b64f",  # state_name_from_zipcode
    "692da81ae032bfaa1e13c418",  # get_total_fee_amount
    "692da850e032bfaa1e13c41a",  # get_category_wise_total_amount
]

# From scanning every in-scope `rules` doc's actions[] for slug == "prompt" and reading
# action.params.fragment.reference_id (prompts) / .version.reference_id (prompt_versions).
# Same order in both lists -- index i in PROMPT_IDS pairs with index i in PROMPT_VERSION_IDS.
PROMPT_IDS = [
    "6ac567b68fe9bfaa29fea68f",  # Bank Statement Document - transaction_details
    "6ac567b68fe9bfaa29fea693",  # Bank Statement Document - cheque_payee_address
    "6ac567b68fe9bfaa29fea697",  # Bank Statement Document - summary_of_charges
    "6ac567b68fe9bfaa29fea69b",  # Bank Statement Document - bank_details
    "6ac567bb8fe9bfaa29fea6df",  # Bank Statement Extraction - borrower_info
    "6ac567bb8fe9bfaa29fea6e3",  # Bank Statement Extraction - collateral_info
    "6ac567bb8fe9bfaa29fea6e7",  # Bank Statement Extraction - name_injection
    "6ac567bc8fe9bfaa29fea6eb",  # Bank Statement Extraction - processor_id_column
    "6ac5da70c1ffbf41d8258c27",  # LAS330 - borrower_info
    "6ac5da71c1ffbf41d8258c2f",  # LAS330 - collateral_info
    "6ac5da79c1ffbf41d8258ca4",  # ls300-pspdoc - borrower_info
    "6ac5da79c1ffbf41d8258cac",  # ls300-pspdoc - collateral_info
    "6ac5da79c1ffbf41d8258cb4",  # ls300-pspdoc - name_injection
    "6ac5da7ac1ffbf41d8258cbc",  # ls300-pspdoc - processor_id_column
    "6ac5da7bc1ffbf41d8258cd4",  # ls300-pspdoc - discovered_fields
    "6acca145546eee5cf2527142",  # Bank Statement Extraction - discovered_fields (v2 migration)
    "6acca142546eee5cf25270fc",  # Bank Statement Extraction - system prompt (fabrix configs.prompt)
]
PROMPT_VERSION_IDS = [
    "6ac567b68fe9bfaa29fea690", "6ac567b68fe9bfaa29fea694", "6ac567b68fe9bfaa29fea698",
    "6ac567b68fe9bfaa29fea69c", "6ac567bb8fe9bfaa29fea6e0", "6ac567bb8fe9bfaa29fea6e4",
    "6ac567bb8fe9bfaa29fea6e8", "6ac567bc8fe9bfaa29fea6ec", "6ac5da71c1ffbf41d8258c28",
    "6ac5da71c1ffbf41d8258c30", "6ac5da79c1ffbf41d8258ca5", "6ac5da79c1ffbf41d8258cad",
    "6ac5da7ac1ffbf41d8258cb5", "6ac5da7ac1ffbf41d8258cbd", "6ac5da7bc1ffbf41d8258cd5",
    "6acca145546eee5cf2527143", "6acca142546eee5cf25270fd",
]

# The processors in the precog source DB still reference the pre-migration Extraction fabrix;
# dump_fixtures.py rewrites that reference to the migrated one.
FABRIX_ID_REMAP = {
    "6ac5e5f2c1ffbf41d82595fb": ("6acca142546eee5cf25270f6", "Hektor Bank Statement Extraction"),
}

# LLM model the rule-engine processor resolves through (processor.model -> bot_run.model ->
# ModelFactory -> FNFModel / ModelVersion / FoundationModel), the same route the other LLM processors
# and bot_service use. These 3 docs are copied verbatim from the dev cluster (read-only) by
# `dump_fixtures.py --dev-uri ...` into the precog database.
MODEL_SOURCE_DB = "pdb-precog-dev"
MODEL_DOC_IDS = {
    "fnf_models": "6a605c3e683499e2a1cb9d0d",       # PC-GemiBench
    "model_versions": "6a60ae74683499e2a1cb9d25",   # gemini-2.5-flash (static version)
    "foundation_model": "6a5f4406683499e2a1cb9cde", # Gemini (engine.framework.models.gemini.GeminiModel)
}
PROCESSOR_MODEL_REFS = {
    "6ac6656b0717bfc9b1625930": {  # Bank Loan Statement Extraction PS (Rule Engine)
        "identifier": MODEL_DOC_IDS["fnf_models"],
        "hidden": False,
        "deleted_status": "N",
        "acl": [],
        "name": "PC-GemiBench",
        "version": {
            "hidden": False,
            "deleted_status": "N",
            "acl": [],
            "type": "static",
            "reference_id": MODEL_DOC_IDS["model_versions"],
        },
    },
}


def oids(ids):
    return {"_id": {"$in": [ObjectId(i) for i in ids]}}


# (src_db, src_coll, dest_db, dest_coll, query, acl_resource_type)
# src_db is inlined (not a named constant) -- these literal source database names
# ("Rule_engine_main_1", "pdb-precog-dev-qa") are only ever read by dump_fixtures.py.
MIGRATIONS = [
    ("Rule_engine_main_1", "fabrix_v2", DEST_FABRIX_DB, "fabrix_v2", oids(FABRIX_IDS), "FabrixV2"),
    ("Rule_engine_main_1", "data_sources", DEST_FABRIX_DB, "data_sources", oids(DATASOURCE_IDS), "DataSource"),
    ("Rule_engine_main_1", "functions", DEST_FABRIX_DB, "functions", oids(FUNCTION_IDS), "Function"),
    ("Rule_engine_main_1", "prompts", DEST_FABRIX_DB, "prompts", oids(PROMPT_IDS), "Prompt"),
    ("Rule_engine_main_1", "prompt_versions", DEST_FABRIX_DB, "prompt_versions", oids(PROMPT_VERSION_IDS), "PromptVersion"),
    ("Rule_engine_main_1", "sections", DEST_FABRIX_DB, "sections", {"fabrix.reference_id": {"$in": FABRIX_IDS}}, "Section"),
    ("Rule_engine_main_1", "rule_blocks", DEST_FABRIX_DB, "rule_blocks", {"fabrix.reference_id": {"$in": FABRIX_IDS}}, "RuleBlock"),
    ("Rule_engine_main_1", "rules", DEST_FABRIX_DB, "rules", {"fabrix.reference_id": {"$in": FABRIX_IDS}}, "Rule"),
    ("Rule_engine_main_1", "rule_conditions", DEST_FABRIX_DB, "rule_conditions", {}, "RuleCondition"),
    ("Rule_engine_main_1", "rule_actions", DEST_FABRIX_DB, "rule_actions", {}, "RuleAction"),
    ("Rule_engine_main_1", "rule_types", DEST_FABRIX_DB, "rule_types",
     {"slug": {"$in": ["validation", "transformation", "extraction"]}}, "RuleType"),
    ("pdb-precog-dev-qa", "bot", DEST_PRECOG_DB, "bot", oids(BOT_IDS), "Bot"),
    ("pdb-precog-dev-qa", "processors", DEST_PRECOG_DB, "processors", oids(PROCESSOR_IDS), "Processor"),
    ("pdb-precog-dev-qa", "processor_types", DEST_PRECOG_DB, "processor_types",
     oids(PROCESSOR_TYPE_IDS), "ProcessorType"),
]
