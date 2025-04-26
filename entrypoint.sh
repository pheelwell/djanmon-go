#!/bin/sh
# Abort on any error
set -e

# Wait for the database to be ready (optional but recommended)
# Example for PostgreSQL:
# while ! nc -z $DB_HOST $DB_PORT; do
#   echo "Waiting for database..."
#   sleep 1
# done
# echo "Database ready."

echo "Applying database migrations..."
# Run migrations using the manage.py inside the djanmongo directory
python djanmongo/manage.py migrate --noinput

echo "Starting Gunicorn..."
# Execute the command passed as arguments to this script (the CMD in Dockerfile)
exec "$@" 