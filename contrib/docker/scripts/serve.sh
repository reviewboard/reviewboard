#!/bin/sh

gunicorn \
    --bind=0.0.0.0:8080 \
    --worker-tmp-dir=/dev/shm \
    --log-level=debug \
    --log-file=- \
    --timeout=${REQUEST_TIMEOUT} \
    --workers=${NUM_WORKERS} \
    --threads=${NUM_THREADS} \
    ${GUNICORN_FLAGS} \
    reviewboard.wsgi
