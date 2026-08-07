#!/bin/sh
set -e

# Dispatch: bare flags (or no args) start the API server; a leading word
# (alembic, sh, ...) runs that command as-is. Lets one image serve the app,
# run migrations (Fly release_command), and open a shell.
if [ -z "$1" ] || [ "${1#-}" != "$1" ]; then
    set -- uvicorn apps.main:app "$@"
fi

exec "$@"
