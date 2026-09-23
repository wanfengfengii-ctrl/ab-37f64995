#!/bin/sh
# Render the runtime API config from environment variables.
# nginx's own 20-envsubst hook already renders default.conf.template.
set -eu

export API_BASE_URL="${API_BASE_URL:-}"
envsubst '$API_BASE_URL' \
  < /usr/share/nginx/html/env-config.template.js \
  > /usr/share/nginx/html/env-config.js
