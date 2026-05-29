#!/usr/bin/env sh
set -e

# Wait for Postgres to accept connections to the application DB. Uses the same
# TLS settings as the app so we don't false-fail against a TLS-only server.
ATTEMPTS=0
MAX_ATTEMPTS="${DB_WAIT_ATTEMPTS:-30}"
until python -c "
import asyncio, os, ssl
import asyncpg

require_ssl = os.environ.get('PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__REQUIRE_SSL','false').lower() == 'true'
ca = os.environ.get('PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__SSL_CA_FILE') or None
verify_host = os.environ.get('PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__SSL_VERIFY_HOSTNAME','true').lower() == 'true'

# Explicit False (NOT None) so asyncpg doesn't fall back to ssl='prefer'
# and silently upgrade the wire. Same reason as app/db.py.
ssl_arg = False
if require_ssl:
    if ca:
        ssl_arg = ssl.create_default_context(cafile=ca)
        if not verify_host:
            ssl_arg.check_hostname = False
            ssl_arg.verify_mode = ssl.CERT_REQUIRED
    else:
        ssl_arg = True

async def go():
    conn = await asyncpg.connect(
        host=os.environ['PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__HOST'],
        port=int(os.environ.get('PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__PORT','5432')),
        user=os.environ['PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__USERNAME'],
        password=os.environ['PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__PASSWORD'],
        database=os.environ['PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__NAME'],
        ssl=ssl_arg,
    )
    await conn.close()

asyncio.run(go())
"; do
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
        echo "postgres did not become reachable after $MAX_ATTEMPTS attempts" >&2
        exit 1
    fi
    echo "entrypoint: waiting for postgres (attempt $ATTEMPTS/$MAX_ATTEMPTS)"
    sleep 1
done

# Create schema once before forking gunicorn workers — otherwise N workers race
# on CREATE TABLE and one wins while the rest fail with pg_type_typname_nsp_index.
python -m app.init_schema

if [ "${SEED_DB:-true}" = "true" ]; then
    python -m app.seed
fi

exec gunicorn -c gunicorn.conf.py app.main:app
