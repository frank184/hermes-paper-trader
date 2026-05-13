#!/usr/bin/env bash
set -euo pipefail

gateway_pid=""
workspace_pid=""

shutdown() {
  if [ -n "$workspace_pid" ] && kill -0 "$workspace_pid" 2>/dev/null; then
    kill "$workspace_pid" 2>/dev/null || true
  fi
  if [ -n "$gateway_pid" ] && kill -0 "$gateway_pid" 2>/dev/null; then
    kill "$gateway_pid" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
}

trap shutdown TERM INT

export HERMES_HOME="${HERMES_HOME:-/opt/data}"
export HOME="${HOME:-$HERMES_HOME}"
export API_SERVER_KEY="${API_SERVER_KEY:-dev-hermes-api-key}"
export HERMES_API_TOKEN="${HERMES_API_TOKEN:-$API_SERVER_KEY}"
export HERMES_PASSWORD="${HERMES_PASSWORD:-dev-hermes-workspace}"
export COOKIE_SECURE="${COOKIE_SECURE:-0}"
export API_SERVER_ENABLED="${API_SERVER_ENABLED:-true}"
export API_SERVER_HOST="${API_SERVER_HOST:-0.0.0.0}"
export HERMES_DASHBOARD="${HERMES_DASHBOARD:-1}"
export HERMES_DASHBOARD_HOST="${HERMES_DASHBOARD_HOST:-0.0.0.0}"
export HERMES_DASHBOARD_PORT="${HERMES_DASHBOARD_PORT:-9119}"
export HERMES_API_URL="${HERMES_API_URL:-http://127.0.0.1:8642}"
export HERMES_DASHBOARD_URL="${HERMES_DASHBOARD_URL:-http://127.0.0.1:9119}"
export HERMES_CLI_BIN="${HERMES_CLI_BIN:-/opt/hermes/.venv/bin/hermes}"
export HERMES_WORKSPACE_DIR="${HERMES_WORKSPACE_DIR:-$HERMES_HOME/workspace}"

mkdir -p "$HERMES_HOME" "$HERMES_HOME/.hermes" "$HERMES_WORKSPACE_DIR"

/opt/hermes/docker/entrypoint.sh gateway run &
gateway_pid="$!"

for _ in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:8642/health" >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$gateway_pid" 2>/dev/null; then
    wait "$gateway_pid"
    exit $?
  fi
  sleep 1
done

if ! curl -fsS "http://127.0.0.1:8642/health" >/dev/null 2>&1; then
  echo "Hermes gateway did not become healthy on :8642" >&2
  shutdown
  exit 1
fi

chown -R hermes:hermes "$HERMES_HOME" "$HERMES_HOME/.hermes" "$HERMES_WORKSPACE_DIR" 2>/dev/null || true

cd /opt/hermes-workspace
if command -v setpriv >/dev/null 2>&1; then
  hermes_uid="$(id -u hermes)"
  hermes_gid="$(id -g hermes)"
  setpriv --reuid="$hermes_uid" --regid="$hermes_gid" --init-groups node --max-old-space-size=2048 server-entry.js &
else
  su hermes -s /bin/sh -c 'node --max-old-space-size=2048 server-entry.js' &
fi
workspace_pid="$!"

wait -n "$gateway_pid" "$workspace_pid"
status=$?
shutdown
exit "$status"
