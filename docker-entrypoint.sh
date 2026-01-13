#!/bin/bash -x
python manage.py migrate --noinput || exit 1

# Adds reference/link of all static files to a single file.
python3 manage.py collectstatic --noinput --clear --link

# Calculate optimal number of workers based on CPU cores
# Formula: (2 × CPU cores) + 1
# This ensures optimal performance for I/O-bound applications
WORKERS=${WORKERS:-$(python3 -c "import multiprocessing; print((2 * multiprocessing.cpu_count()) + 1)" 2>/dev/null || echo "3")}

echo "Starting uvicorn with $WORKERS workers"

exec "$@"
