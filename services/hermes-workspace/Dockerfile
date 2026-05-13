# syntax=docker/dockerfile:1.6

FROM ghcr.io/outsourc-e/hermes-workspace:latest AS workspace

FROM nousresearch/hermes-agent:latest

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=workspace /app /opt/hermes-workspace
COPY entrypoint.sh /usr/local/bin/hermes-workspace-entrypoint.sh
COPY patch-mcp-marketplace.js /tmp/patch-mcp-marketplace.js

RUN node /tmp/patch-mcp-marketplace.js \
    && rm /tmp/patch-mcp-marketplace.js \
    && chmod +x /usr/local/bin/hermes-workspace-entrypoint.sh

ENV HERMES_WEB_DIST=/opt/hermes/hermes_cli/web_dist \
    HERMES_HOME=/opt/data \
    HOME=/opt/data \
    NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0 \
    HERMES_API_URL=http://127.0.0.1:8642 \
    HERMES_DASHBOARD_URL=http://127.0.0.1:9119 \
    HERMES_CLI_BIN=/opt/hermes/.venv/bin/hermes \
    HERMES_WORKSPACE_DIR=/opt/data/workspace \
    PATH=/opt/hermes/.venv/bin:/opt/data/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

EXPOSE 3000 8642 9119

ENTRYPOINT ["/usr/bin/tini", "-g", "--", "/usr/local/bin/hermes-workspace-entrypoint.sh"]
