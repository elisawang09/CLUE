#!/usr/bin/env bash
#
# Bring up both apps for a study session.
#
#   ./run_study.sh
#
#   baseline dashboard  http://localhost:8501   (condition comes from the link)
#   CLUE                http://localhost:8502
#
# Both stay up continuously. Which condition a participant gets is decided by
# the session token in their link, not by which process is running -- generate
# links with:
#
#   cd baseline_dashboard
#   ../.venv/bin/python -m study.make_sessions --participants 24 \
#       --base-url http://localhost:8501
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$ROOT/.venv/bin/python"

BASELINE_PORT="${BASELINE_PORT:-8501}"
CLUE_PORT="${CLUE_PORT:-8502}"

# Where the baseline's "Open in CLUE" links point. Override when serving from a
# real hostname rather than localhost.
export CLUE_URL="${CLUE_URL:-http://localhost:$CLUE_PORT}"

if [[ ! -x "$PYTHON" ]]; then
    echo "No virtualenv at $PYTHON" >&2
    exit 1
fi

if [[ ! -d "$ROOT/baseline_dashboard/data/modeled" ]]; then
    echo "Modeled data source missing. Build it first:" >&2
    echo "  cd baseline_dashboard && ../.venv/bin/python -m datasource.build" >&2
    exit 1
fi

cleanup() {
    if [[ -n "${CLUE_PID:-}" ]] && kill -0 "$CLUE_PID" 2>/dev/null; then
        kill "$CLUE_PID" 2>/dev/null || true
        wait "$CLUE_PID" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

echo "Starting CLUE on :$CLUE_PORT"
(cd "$ROOT/demo" && "$PYTHON" -m streamlit run main.py \
    --server.port "$CLUE_PORT" --server.headless true) &
CLUE_PID=$!

echo "Starting baseline dashboard on :$BASELINE_PORT (CLUE_URL=$CLUE_URL)"
cd "$ROOT/baseline_dashboard"
"$PYTHON" -m streamlit run app.py \
    --server.port "$BASELINE_PORT" --server.headless true
