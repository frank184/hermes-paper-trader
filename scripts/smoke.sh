#!/usr/bin/env bash
set -euo pipefail

curl -fsS http://localhost:8001/health
printf '\n'
curl -fsS http://localhost:8002/health
printf '\n'
curl -fsS http://localhost:8642/health
printf '\n'
curl -fsS -o /dev/null http://localhost:3000/
printf 'hermes-workspace ok\n'
