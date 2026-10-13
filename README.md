# Client Mongo seed

Migrates the real rule-engine and precog objects for the 4 bots/processors that were built and
live-tested against this repo's dev data, plus Hektor's complete `fabrix_v2` catalog, into 3
pre-existing destination databases: `Hektor_fabrix`, `Hektor_precog`, `Hektor_entity`. Every migrated
document is retagged to a single target `client_id`, and every destination database gets a
wildcard-principal (`"*"`) `acl` collection, with every ACL doc's `_id` a real `ObjectId` (matching
the resource it protects), not a string.

## Quick Start (One-Line Execution)

From the `client_mongo_seed` directory, run:

### Windows (PowerShell):
```powershell
# Dry run:
python -m venv venv; .\venv\Scripts\pip install -r requirements.txt; .\venv\Scripts\python seed_client.py --dry-run

# Actual seed:
python -m venv venv; .\venv\Scripts\pip install -r requirements.txt; .\venv\Scripts\python seed_client.py
```

### Windows (Command Prompt / CMD):
```cmd
python -m venv venv && .\venv\Scripts\pip install -r requirements.txt && .\venv\Scripts\python seed_client.py --dry-run
```

### Linux / macOS (Bash):
```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/python seed_client.py --dry-run
```

*(Optional: add `--mongo-uri mongodb://host:port` to target a different MongoDB host)*

> **Note**: Do not copy or zip the `venv/` folder across machines. Always create it fresh on the target machine with the commands above. Calling `.\venv\Scripts\python` directly avoids PowerShell script execution policy errors.

## How this relates to the old seeding script

The old script (`mongo_seeding_script/seed.py`) wrote one hand-authored fixture bundle ("Fiserv DNA
Masking") into static dev databases (`pdb-pi-dev`, `pdb-precog-dev`, `pdb-entity-dev`), loading its
documents from JSON files in a `data/` directory via `bson.json_util`. This directory follows the
exact same pattern — `seed_client.py` loads JSON fixtures from its own `data/` directory and
upserts them into the destination databases, with no database-to-database copy at seed time.

The difference is where the fixtures came from: the old script's `data/*.json` was hand-authored
for one fixture bundle. This directory's `data/*.json` is a real export — every document was
dumped, once, from the live `Rule_engine_main_1` (fabrix) and `pdb-precog-dev-qa` (precog)
databases by `dump_fixtures.py`, with each document's `client_id` already overwritten and its ACL
doc already built in. Nothing in `data/` is fabricated.

**Why this matters for a new environment**: `seed_client.py` never opens a connection to
`Rule_engine_main_1` or `pdb-precog-dev-qa` — it only reads the static files already sitting in
`data/`. Copy this whole directory (including `data/`) to a new environment and
`python seed_client.py` works there even though that environment has no access to the original
source databases. `dump_fixtures.py` is the opposite: a dev-only, one-time tool that *does* need
live source access, and you only run it again if the migration's scope changes (see
"Id-derivation methodology" below) and the fixtures need regenerating.

## Directory layout

```
client_mongo_seed/
  data/                  # the fixtures seed_client.py actually reads (18 files, ~4187 docs total)
  seed_client.py          # THE one command to run: loads data/*.json, upserts into the 3 dbs
  dump_fixtures.py        # dev-only: regenerates data/*.json from the live source databases
  config.py               # shared constants + id lists (used by dump_fixtures.py, and for the
                           # destination db names seed_client.py needs)
  acl.py                   # ACL doc builder (used by dump_fixtures.py)
  connections.py           # builds Hektor_entity.connections docs from each bot's own
                           # sources[]/destinations[] (used by dump_fixtures.py)
  requirements.txt
  README.md
```

## Scope

- **Fabrix side: all 17 live `fabrix_v2` docs** — Hektor's complete catalog of 15 original live
  fabrixes, the one real HC3 fabrix ("HC3 Fiserv DNA Masking"; a second, junk HC3 doc literally
  named "test" is excluded), plus the new "Notice of Transfer Letter Masking" fabrix authored later
  this session (6 `scramble` rules against `RegexBlockAdapter`/`RegexBlockParser`-extracted fields —
  see `docs/migration/` or the session history for that bot's own design). Every
  section/rule_block/rule/function/prompt/data_source that any of those 17 fabrixes actually
  reference is pulled along with them.
- **Precog side: only the 4 bots/processors that were actually built and run this session** —
  HC3 Fiserv DNA Masking, Hektor Bank Statement Document, Bank Loan Statement Extraction (the 3
  covered by `postman/hektor-hc3-botruns.postman_collection.json`'s original folders), and Notice of
  Transfer Letter Masking (covered by that same collection's later-added folder). The other 12
  Hektor fabrixes never got a matching `RuleEngineTransformationProcessor`/`MaskingProcessor` doc
  built, so there is nothing real to migrate for them on the precog side.
- **Global rule-engine catalogs** (`rule_conditions`, `rule_actions`, `rule_types`) are copied in
  full (or, for `rule_types`, filtered to slugs `validation`/`transformation` only), since they are
  shared reference data, not scoped to any one fabrix or client.
- **`processor_types`**: the 2 processor-type docs (`pi/data/process/masking`,
  `pi/data/process/transformation`) that the 4 in-scope `processors` docs reference via their own
  `type.reference_id` field — without these, a seeded `processors` doc points at a `processor_types`
  id that doesn't exist in the destination database. The new Notice of Transfer Letter Masking
  processor reuses the same `pi/data/process/masking` type as HC3's — no new processor_type needed.
- **`connections`** (entity side): one standalone doc per source/destination entry across all 4
  bots — see "`Hektor_entity.connections`" below. Not part of the fabrix/precog `MIGRATIONS` table
  since these are derived from the already-migrated `bot` docs, not queried from a source database.

## Why `fabrix_configs` and `state_types` are excluded

Dropped entirely, per explicit decision during planning — not needed for this migration's target
bundles, and not worth the risk of carrying along config documents or type catalogs. The old script
already provides whatever static reference data those collections might have.

## `Hektor_entity.connections`

Confirmed by direct query against the source databases: there was zero *pre-existing* Hektor/HC3
entity data to migrate (`pdb-precog-dev-qa.connections` is empty, and the separate, unrelated
`pdb-entity-dev` database — a different product domain entirely, products/consumers/orders, not
bot connections — has no matching docs either). `Hektor_entity.connections` is instead populated
with **real, derived** resource documents: `connections.py`'s `build_connections_for_bot()` walks
each of the 4 migrated `bot` docs' own `configuration.sources[]`/`destinations[]` entries (6
total: HC3 has 1 source + 1 destination, Notice of Transfer Letter Masking has 1 source + 1
destination, the other 2 bots have 0 sources + 1 destination each — they use `input_text`/
`input_file` run params instead of a configured source) and promotes each one to a standalone
`connections` doc, matching the real schema confirmed against a sample export
(`pdb-entity-dev.connections.json`: top-level `name`/`type`/`category`/`connection_config`/
`connection_type`, the same shape a bot embeds inline).

Every bot's source/destination entry in `data/bot.json` ends up with a `connection_ref` pointing
at its new connections doc — HC3's bot already carried `connection_ref.reference_id` pointers
(`6a60e036b5e1889f1a06f8a2` for its source, `69ccadf10ab6f287f499f4fb` for its destination) that
resolved to nothing anywhere in this dev environment; those exact ids are reused as the new
connections docs' own `_id` so the migration backs the existing dangling pointer instead of
creating an orphaned duplicate. The other 3 bots' entries had no `connection_ref` at all; one is
minted fresh (a plain new `ObjectId`) and injected, matching the convention every real
connection-bearing entry in the sample export already follows.

`Hektor_entity` additionally keeps a single blanket wildcard ACL doc
(`_id=ObjectId("000000000000000000000000")`, `resource.identifier="*"`) alongside the 6 real
per-connection ACL docs — a belt-and-suspenders fallback in case some future consumer expects an
entity-level ACL that isn't tied to any specific connection.

## Id-derivation methodology

Every "fixed" id list in `config.py` was derived once, directly against the live databases, not
guessed, and only matters to `dump_fixtures.py` (the fixture files in `data/` are what
`seed_client.py` actually reads). Re-run the same recipe below, then re-run `dump_fixtures.py`, if
`FABRIX_IDS` or `BOT_IDS`/`PROCESSOR_IDS` ever need to change (e.g. a new fabrix is added for this
client):

- **`FABRIX_IDS`**: queried `fabrix_v2` for Hektor + HC3 owned docs with
  `deleted_status != "Y"`, manually excluding the one junk HC3 "test" doc, plus the new Notice of
  Transfer Letter Masking fabrix's own id (known directly — it was authored, not discovered, via
  `CLIENTS/NoticeOfTransfer(Masking)/notice_of_transfer_masking_migrate.py` in api-entity-fabrix).
- **`BOT_IDS` / `PROCESSOR_IDS`**: the 3 original bot/processor pairs covered by
  `postman/hektor-hc3-botruns.postman_collection.json`'s original folders, plus the new Notice of
  Transfer Letter Masking bot/processor pair created via REST later this session (covered by that
  same collection's newer folder) — no derivation needed for any of these 4, their ids are already
  known from when they were built/authored.
- **`DATASOURCE_IDS`**: read each of the 17 `fabrix_v2` docs' own `data_source.reference_id` field.
  Only 16 entries come out — "Hektor Customer Data CSV" has no `data_source` set on its fabrix doc,
  which is a real property of that fabrix, not a migration omission.
- **`sections` / `rule_blocks` / `rules`**: *not* hardcoded id lists. `sections` and `rule_blocks`
  carry a `fabrix: {reference_id, name}` embedded reference but have **no `client_id` field at all**;
  `rules` carries both `fabrix` and `client_id`. `rule_blocks` is a thin join doc (fabrix + section +
  rule pointers) — the real `conditions`/`actions` live on the `rules` doc it points to. So the only
  correct filter for all three is `{"fabrix.reference_id": {"$in": FABRIX_IDS}}`; a `client_id` filter
  would silently miss `sections`/`rule_blocks` entirely since they don't have that field. This query
  currently matches 35 sections, 920 rule_blocks, 904 rules — far too many to pin as literal ids, so
  `config.py` keeps this one live/query-driven instead of enumerated.
- **`FUNCTION_IDS` / `PROMPT_IDS` / `PROMPT_VERSION_IDS`**: scanned every in-scope `rules` doc's
  `actions[]` array for `slug == "custom_function"` (reads
  `action.params.function_ref.reference_id`) and `slug == "prompt"` (reads
  `action.params.fragment.reference_id` for the prompt, and
  `action.params.fragment.version.reference_id` for the prompt version — `PROMPT_IDS` and
  `PROMPT_VERSION_IDS` are kept in matching order, index-for-index). This found exactly 3 functions
  and 15 prompts/prompt_versions across the 904 original in-scope rules — 11 of the first 16
  fabrixes are pure deterministic (masking/transform) cohorts with no LLM section at all, which
  matches this session's earlier findings when those bots were built and tested. The new Notice of
  Transfer Letter Masking fabrix's 6 rules are all `scramble` (no `custom_function`/`prompt`
  actions), so it contributes nothing new to either list.
- **`PROCESSOR_TYPE_IDS`**: read each of the first 3 in-scope `processors` docs' own
  `type.reference_id` field. HC3 Fiserv DNA Masking points at the `pi/data/process/masking`
  processor_type; the other 2 (both `RuleEngineTransformationProcessor`) point at the same
  `pi/data/process/transformation` processor_type — 2 distinct ids shared across all 4 processors
  (the new Notice of Transfer Letter Masking processor reuses `pi/data/process/masking` too).
- **`connections` ids**: not hardcoded at all — `connections.py` derives them live from each bot
  doc's own `configuration.sources[]`/`destinations[]`, reusing an entry's existing
  `connection_ref.reference_id` when present (HC3's 2 entries) or minting a fresh `ObjectId` when
  absent (the other 4 entries). Re-running `dump_fixtures.py` regenerates `connections.json` from
  whatever `bot.json` ends up containing, so this needs no separate id list to maintain.

## The MIGRATIONS table (`config.py`), row by row

This table drives `dump_fixtures.py` only — it's how the fixtures in `data/` were produced, not
something `seed_client.py` reads at seed time.

| Source collection | Dest collection | Filter | Why |
|---|---|---|---|
| `fabrix_v2` | `fabrix_v2` | `_id in FABRIX_IDS` | the 17 in-scope fabrixes |
| `data_sources` | `data_sources` | `_id in DATASOURCE_IDS` | each fabrix's own data source |
| `functions` | `functions` | `_id in FUNCTION_IDS` | functions referenced by in-scope rules |
| `prompts` | `prompts` | `_id in PROMPT_IDS` | prompts referenced by in-scope rules |
| `prompt_versions` | `prompt_versions` | `_id in PROMPT_VERSION_IDS` | versions of those prompts |
| `sections` | `sections` | `fabrix.reference_id in FABRIX_IDS` | no `client_id` field exists on this collection |
| `rule_blocks` | `rule_blocks` | `fabrix.reference_id in FABRIX_IDS` | same; thin join docs, no `client_id` |
| `rules` | `rules` | `fabrix.reference_id in FABRIX_IDS` | matches the same scoping as its own join docs |
| `rule_conditions` | `rule_conditions` | none (full copy) | shared global catalog |
| `rule_actions` | `rule_actions` | none (full copy) | shared global catalog |
| `rule_types` | `rule_types` | `slug in (validation, transformation)` | only these 2 types are in scope |
| `bot` | `bot` | `_id in BOT_IDS` | the 4 tested bots |
| `processors` | `processors` | `_id in PROCESSOR_IDS` | the 4 tested processors |
| `processor_types` | `processor_types` | `_id in PROCESSOR_TYPE_IDS` | the 2 types those 4 processors reference |

Every row additionally applies `deleted_status != "Y"` (tolerant of a missing field, not an exact
`"N"` match — some collections in this schema don't carry `deleted_status` at all, and a missing
field should count as live).

## `client_id` retagging

Every migrated document — including global catalogs that had no `client_id` field at all in the
source, and the HC3-owned fabrix/bot/processor — gets `client_id` unconditionally overwritten to
`TARGET_CLIENT_ID` (`691ad32be2653616d96af2d5`) on write. This is deliberate and unconditional: the
destination databases belong to one client, so every object in them should carry that client's id
regardless of who originally owned it.

## ACLs

`acl.py`'s `build_acl_doc(resource_id, resource_type)` (used by `dump_fixtures.py` when it builds
`data/acl_fabrix.json`/`acl_precog.json`/`acl_entity.json`) builds one ACL doc per migrated
document, with `_id` set to the resource's own `_id` (not prefixed with the resource type, e.g.
`6ac5e5f6c1ffbf41d8259641` rather than `FabrixV2:6ac5e5f6c1ffbf41d8259641`) so re-running the seed
upserts the same doc rather than creating duplicates, and `principal: "*"` (wildcard — matches this
migration's requirement, unlike the old script's per-user `principal`).

**`_id` is a real `bson.ObjectId`, not a string** — confirmed every migrated collection's own `_id`
(`fabrix_v2`, `rules`, `bot`, `processors`, etc.) is a genuine `ObjectId`, so `build_acl_doc()`
converts `resource_id` to `ObjectId` before using it as `_id` (it only ever looked like one as a
plain string before). `resource.identifier` stays a string, matching the real ACL convention seen
in the live source databases. `build_entity_blanket_acl_doc()` (the one extra doc appended to
`data/acl_entity.json`, alongside the 6 real per-connection ACL docs — see
"`Hektor_entity.connections`" above) uses a fixed all-zero `ObjectId("000000000000000000000000")`
sentinel since no single resource backs that particular row, but its `_id` should still be
`ObjectId`-typed for consistency with every other row in the collection.

## Running it

### One-Line Execution

**PowerShell (Windows):**
```powershell
python -m venv venv; .\venv\Scripts\pip install -r requirements.txt; .\venv\Scripts\python seed_client.py --dry-run
```
*(To run for real, remove `--dry-run`:)*
```powershell
python -m venv venv; .\venv\Scripts\pip install -r requirements.txt; .\venv\Scripts\python seed_client.py
```

**Command Prompt / CMD (Windows):**
```cmd
python -m venv venv && .\venv\Scripts\pip install -r requirements.txt && .\venv\Scripts\python seed_client.py --dry-run
```

**Linux / macOS (Bash):**
```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/python seed_client.py --dry-run
```

> **Tip**: Calling `.\venv\Scripts\python` and `pip` directly avoids needing to activate the environment or dealing with PowerShell execution policy restrictions.

---

### Step-by-Step (Alternative)

```bash
# 1. Create a local virtual environment
python -m venv venv

# 2. Activate it
# Windows (PowerShell): .\venv\Scripts\Activate.ps1
# Windows (CMD):        .\venv\Scripts\activate.bat
# Linux / macOS:        source venv/bin/activate

# 3. Install requirements
pip install -r requirements.txt

# 4. Run the seed script
python seed_client.py --dry-run
python seed_client.py
```

> **Note**: Virtual environments (`venv`) contain machine-specific absolute paths and should never be copied between different machines. Always create the `venv` fresh on the target machine.

Either way, no separate `--dry-run`/live-source step is needed — `seed_client.py` only reads the
JSON files already in `data/` and writes to the destination databases.

```bash
# Optional: point at a different Mongo host
python seed_client.py --mongo-uri mongodb://some-other-host:27017
```

The script is idempotent — every write is `replace_one(..., upsert=True)` keyed by the fixture
document's own `_id` (ids are preserved, never regenerated, so cross-collection references such as
`rules.fabrix.reference_id` or `processors.fabrix.reference_id` keep resolving correctly), and ACL
docs use a deterministic `_id` too. Running it twice produces identical counts, so it is safe to
re-run, including the user's own final validation run.

## Verification

```python
from pymongo import MongoClient
from bson import ObjectId
c = MongoClient("mongodb://localhost:27017")

assert c["Hektor_fabrix"]["fabrix_v2"].count_documents({}) == 17
assert c["Hektor_fabrix"]["rule_blocks"].count_documents({}) == 927
assert c["Hektor_fabrix"]["rules"].count_documents({}) == 910
assert c["Hektor_fabrix"]["sections"].count_documents({}) == 37
assert c["Hektor_fabrix"]["functions"].count_documents({}) == 3
assert c["Hektor_fabrix"]["prompts"].count_documents({}) == 15
assert c["Hektor_fabrix"]["prompt_versions"].count_documents({}) == 15
assert c["Hektor_fabrix"]["data_sources"].count_documents({}) == 16
assert c["Hektor_fabrix"]["rule_types"].count_documents({}) == 2
assert c["Hektor_precog"]["bot"].count_documents({}) == 4
assert c["Hektor_precog"]["processors"].count_documents({}) == 4
assert c["Hektor_precog"]["processor_types"].count_documents({}) == 2
assert c["Hektor_entity"]["connections"].count_documents({}) == 6

for d in c["Hektor_fabrix"]["fabrix_v2"].find():
    assert d["client_id"] == "691ad32be2653616d96af2d5"

for dbn in ["Hektor_fabrix", "Hektor_precog", "Hektor_entity"]:
    acl = c[dbn]["acl"]
    assert acl.count_documents({}) > 0
    sample = acl.find_one({})
    assert isinstance(sample["_id"], ObjectId)
    assert sample["principal"] == "*"

# every bot source/destination's connection_ref resolves to a real Hektor_entity.connections doc
for b in c["Hektor_precog"]["bot"].find({}):
    cfg = b.get("configuration", {})
    for key in ("sources", "destinations"):
        for entry in cfg.get(key, []):
            ref = (entry.get("connection_ref") or {}).get("reference_id")
            if ref:
                assert c["Hektor_entity"]["connections"].find_one({"_id": ObjectId(ref)})

# idempotency: run `python seed_client.py` a second time, confirm identical counts both times
```

Also spot-check that a cross-reference survived, e.g. `Hektor_precog.processors`' fabrix reference
for the Bank Loan Statement Extraction processor still resolves to a real doc in
`Hektor_fabrix.fabrix_v2` — this should hold automatically since `_id`s are preserved, not
regenerated.

## Postman collections

- `postman/hektor-hc3-botruns.postman_collection.json` (api-entity-fabrix repo, delivered earlier,
  later extended with a 4th folder) covers running all 4 bots live and inspecting their output.
- `postman/client-seed-verification.postman_collection.json` (api-entity-fabrix repo) is new:
  read-only GET requests against the actual fabrix (`:8000`) and precog (`:5000`) REST APIs for
  every collection this script seeds — `fabrix_v2`, `sections`, `rule_blocks`, `rules`,
  `rule_conditions`, `rule_actions`, `rule_types`, `prompts`/`prompt_versions`, `data_sources`,
  `functions` under "Fabrix APIs", and `bot`, `processors`, `processor_types` under "Precog APIs" —
  so the seed can be checked through the application layer, not just by querying Mongo directly.
  Its collection variables are pre-filled with real ids from this migration (e.g.
  `fabrix_id_bank_stmt_doc`, `hc3_bot_id`, `processor_type_masking_id`).

**Caveat (both collections)**: their requests hit the **live** precog/fabrix services, which are
currently configured against `pdb-precog-dev-qa`/`Rule_engine_main_1`. Actually exercising them
against the newly-seeded `Hektor_fabrix`/`Hektor_precog` databases requires pointing those
services' own DB env vars at the new databases first — a separate follow-up step, out of scope for
this seeding script.

**Caveat (`client-seed-verification` only)**: `fabrix_v2`, `functions`, `data_sources` (fabrix
side) and `bot`, `processor` (precog side) are ACL-gated — their list/detail views filter by the
request token's tenant/ACL ownership (`acl.filters.acl_filter.AclResourceFilter`). An empty list or
a 404 on those specific requests does not necessarily mean the seed failed; it can mean the
token's user/tenant doesn't own the migrated documents. Use a super-admin or `service-account-*`
token to see seeded data regardless of ownership. `sections`, `rule_blocks`, `rules`,
`rule_conditions`, `rule_actions`, `rule_types`, `prompts`/`prompt_versions`, and `processor_types`
are not ACL-gated, so any authenticated token sees them.

## Local File Subscription (connection + connection runtimes)

`local_sub.py` authors the Local File Subscription that api-connections (`manage.py run_local_file_sub`) runs. It is **not** dumped from a
source DB; `dump_fixtures.py` re-applies it so regenerating the fixtures keeps it.

| Fixture | What `local_sub.py` puts in it |
|---|---|
| `data/connections.json` | 1 connection `6ad0000000000000000f1e01` "Hektor - Local File Sub (Bank Statements)" (type `local_file_adapter`, folder in `connection_config.config_value`) |
| `data/connection_runtime.json` (seeded into the entity DB) | runtime A `bot:6ac6656b0717bfc9b1625932:local_file_adapter:<connection>` `PAUSED`; runtime B `agent:6acdd6c63d578a20bff2713a:local_file_adapter:<connection>` `RUNNING` (the real "Hektor Agent", see below) |
| `data/acl_entity.json` | the connection's ACL entry |
| `data/bot.json` | the Statement bot's embedded subscriber source removed (the subscription no longer depends on any bot) |

The old bot-embedded connection `6acc9594d270343c5d96569c` and its ACL entry were removed from the fixtures. The seed only upserts, so a database seeded earlier still holds that connection: it is harmless but orphaned.
The Notice bot keeps its own subscriber source (not migrated yet).

`python local_sub.py [--folder P] [--dry-run]` re-applies it to `data/`. `python seed_client.py --bot-id <bot> --path <folder>` sets the watched folder:
for a bot with a `local_file` runtime it changes that runtime's connection; for a bot that still embeds a subscriber source it changes the source and its connection.

## Notice of Transfer changes (edited in the fixtures after the dump)

These fixtures were edited by hand after `dump_fixtures.py` ran, so **re-running the dump from a source DB would overwrite them**. Backups of the files before each change are in the `data_backup_before_*` folders.

| Change | Fixtures | Resources | Script for an already-seeded DB (`api-entity-fabrix/CLIENTS/Hektor/`) |
|---|---|---|---|
| Bank Statement fabrix `6acca142…70f6` -> Notice of Transfer fields (8 regex + 2 LLM rules, system prompt, datasource features) | `rules`, `rule_blocks`, `acl_fabrix`, `prompts`, `prompt_versions`, `data_sources`, `fabrix_v2` | `assets/BankStatementParser/notice_of_transfer_input_*.txt` (UTF-8, UTF-16LE with/without BOM, random UTF-16LE) | `hektor_statement_notice_update.py` (Mongo) or `hektor_fabrix_api_update.py` (fabrix API) or `hektor_notice_migrate.py` (creates both fabrixes through the API) |
| Masking fabrix `6ac7a348…90a9` masks `data.from_account_number` / `data.to_account_number` with `{fill:X}{last4}`; masking bot reads the parser JSON | `rules`, `rule_blocks`, `acl_fabrix`, `data_sources`, `connections`, `bot`, `processors` | `assets/BankStatementParser/notice_parser_output_sample.json` | `hektor_masking_notice_fields_update.py` (`--fabrix-only` for just the fabrix db) or `hektor_fabrix_api_update.py` |
| `file_url` input param on both processors (relative or absolute path; `input_file` wins) and `input_json` (type json) on the masking processor (order: `input_file`, `input_json`, `file_url`) | `processors` | – | `hektor_file_url_param_update.py` (precog db) |
| `substitute_value` / `scramble` rule-action text and params | `rule_actions` | – | `hektor_fabrix_api_update.py` (first step; `--skip-rule-actions` to leave it) |

`seed_client.py` only **upserts**: on a database that already holds the old loan-statement rules (35) it adds the new documents but does not delete the old ones. Use one of the scripts above (dry-run by default, backup + `--restore`) on such a database, or seed a fresh one.

## Agents database `Hektor_agent_4`

`seed_client.py` also seeds `Hektor_agent_4` (`DEST_AGENT_DB` in `config.py`) from four static fixtures, which are an **exact copy** of the `pdb-agents` database as it was when taken: `agents.json` (1: "Hektor Agent" `6acdd6c63d578a20bff2713a`) and `state_types.json` (47), documents unchanged (ids, client ids, dates, nested data). The source's 8 `executions` are deliberately not seeded (run history of the source environment), so the new database starts with none.
Only the ACL differs from the source: the source had one entry for the agent with `principal: user/4e72c605-...`; `data/acl_agent.json` has the same entry (`agent/6acdd6c6...`) with the wildcard principal `*` and actions read/write, like every other seeded database. There is no dump step and no source-database setting: the fixtures are the source of truth (`dump_fixtures.py` does not touch them).
The Local File Subscription runtimes now point at that agent: the **agent runtime is `RUNNING`** with the real agent id (runtime name and `context.reference_id`), the **bot runtime is `PAUSED`**. Swap the two statuses in `connection_runtime.json` (and `local_sub.py`) to feed the bot instead.
