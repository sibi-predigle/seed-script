#!/usr/bin/env bash
# Seeds the client databases (Hektor_fabrix_4, Hektor_precog_4, Hektor_entity_4, Hektor_agent_4) from data/*.json on Linux / macOS.
#
#   ./run_seed.sh --dry-run                       # counts and sample ids, writes nothing (do this first)
#   ./run_seed.sh                                 # seed
#   MONGO_URI="mongodb://user:pass@host:27017" ./run_seed.sh
#   RESOURCES_DIR=/opt/predigle/precog/resources ./run_seed.sh
#   ./run_seed.sh --bot-id 6ac6656b0717bfc9b1625932 --path /opt/home/predigle/inbox/bank_statements
#
# Environment:
#   MONGO_URI      Mongo connection string (default mongodb://localhost:27017)
#   RESOURCES_DIR  precog `resources/` folder that receives the bundled sample / mapping files
#                  (default ../api-entity-precog/resources when it exists, otherwise the copy is skipped)
#   SEED_PYTHON    python to use (default python3, then python)
#   NO_INSTALL=1   do not create .venv / install requirements (use the python as it is)
#
# Every other argument goes to seed_client.py unchanged (--dry-run, --bot-id, --path, --mongo-uri, --resources-dir).
# The seed only upserts by _id: re-running is safe, and it never deletes documents.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PY="${SEED_PYTHON:-}"
if [ -z "$PY" ]; then
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python >/dev/null 2>&1; then PY=python
  else echo "[ERROR] python3 not found; install Python 3.9+ or set SEED_PYTHON" >&2; exit 1
  fi
fi

if [ "${NO_INSTALL:-0}" != "1" ]; then
  if [ ! -d .venv ]; then
    echo "[+] creating .venv"
    "$PY" -m venv .venv
  fi
  # shellcheck disable=SC1091
  . .venv/bin/activate
  PY=python
  echo "[+] installing requirements"
  python -m pip install --quiet --disable-pip-version-check -r requirements.txt
fi

ARGS=("$@")
has_arg() { local a; for a in "${ARGS[@]:-}"; do [ "$a" = "$1" ] && return 0; done; return 1; }

if ! has_arg --mongo-uri; then
  ARGS+=(--mongo-uri "${MONGO_URI:-mongodb://localhost:27017}")
fi

if ! has_arg --resources-dir; then
  if [ -n "${RESOURCES_DIR:-}" ]; then
    ARGS+=(--resources-dir "$RESOURCES_DIR")
  elif [ ! -d ../api-entity-precog/resources ]; then
    echo "[!] ../api-entity-precog/resources not found and RESOURCES_DIR not set: bundled resource files will NOT be copied"
    ARGS+=(--resources-dir "")
  fi
fi

echo "[+] seed_client.py ${ARGS[*]}" | sed -E 's#(mongodb(\+srv)?://)[^@ ]*@#\1***@#'
exec "$PY" seed_client.py "${ARGS[@]}"
