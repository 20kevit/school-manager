#!/bin/sh
set -e

echo "==> Waiting for PostgreSQL to be ready..."

python -c "
import os, sys, time
import psycopg2
url = os.environ.get('DATABASE_URL', '')
if not url:
    print('DATABASE_URL not set, skipping DB wait.')
    sys.exit(0)
for i in range(30):
    try:
        psycopg2.connect(url)
        print('    Database is ready.')
        sys.exit(0)
    except psycopg2.OperationalError:
        print(f'    Attempt {i+1}/30: database not ready, retrying in 1s...')
        time.sleep(1)
print('    ERROR: Could not connect to database after 30 attempts.')
sys.exit(1)
"

echo "==> Running database migrations..."
flask db upgrade

if [ -n "$SEED_MODE" ]; then
    if [ "$SEED_MODE" = "demo" ]; then
        echo "==> Seeding database with demo data (SEED_MODE=demo)..."
        flask seed-demo
    elif [ "$SEED_MODE" = "basic" ]; then
        echo "==> Seeding database with basic data (SEED_MODE=basic)..."
        flask seed
    else
        echo "==> Unknown SEED_MODE='$SEED_MODE', skipping seed."
    fi
else
    echo "==> SEED_MODE not set, skipping seed."
fi

echo "==> Starting application..."
exec "$@"
