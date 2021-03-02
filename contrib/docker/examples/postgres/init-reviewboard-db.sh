#!/bin/sh

set -e

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" <<END
    CREATE USER reviewboard;
    CREATE DATABASE reviewboard;
    GRANT ALL PRIVILEGES ON DATABASE reviewboard TO reviewboard;
END
