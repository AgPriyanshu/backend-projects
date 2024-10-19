#!/bin/bash -x
python manage.py migrate --noinput || exit 1

# Adds reference/link of all static files to a single file.
python3 manage.py collectstatic --noinput --clear --link

exec "$@"
