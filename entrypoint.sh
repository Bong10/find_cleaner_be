#!/bin/sh

# Wait for Redis
if [ "$REDIS_HOST" = "redis" ]; then
    echo "Waiting for redis..."
    while ! nc -z $REDIS_HOST $REDIS_PORT; do
      sleep 0.1
    done
    echo "Redis started"
fi

# Wait for Postgres (if used)
if [ "$DB_ENGINE" = "django.db.backends.postgresql" ]; then
    echo "Waiting for postgres..."
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
fi

# Optionally run migrations/collectstatic (default: true). Disable in worker.
if [ "${RUN_MIGRATIONS}" != "false" ] && [ "${RUN_MIGRATIONS}" != "0" ]; then
  echo "Running migrations..."
  python manage.py migrate

  echo "Collecting static files..."
  python manage.py collectstatic --no-input
else
  echo "Skipping migrations and collectstatic (RUN_MIGRATIONS=${RUN_MIGRATIONS})"
fi

exec "$@"
