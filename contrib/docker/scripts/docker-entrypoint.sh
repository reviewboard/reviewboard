#!/bin/bash

set -ex

if [ "$WAIT_FOR_DB" == "yes" ]; then
    echo "Waiting for ${DATABASE_TYPE}..."

    if [ "$DATABASE_TYPE" == "postgresql" ]; then
        until PGPASSWORD="$DATABASE_PASSWORD" \
              psql -h "${DATABASE_SERVER}" \
                   -U "${DATABASE_USERNAME}" \
                   "${DATABASE_NAME}" \
                   -c '\q'; do
            sleep 1
       done
    elif [ "$DATABASE_TYPE" == "mysql" ]; then
        until MYSQL_PWD="${DATABASE_PASSWORD}" \
              mysql -h "${DATABASE_SERVER}" \
                    -u "${DATABASE_USERNAME}" \
                    "${DATABASE_NAME}" \
                    -e "exit"; do
            sleep 1
       done
    fi

    echo "${DATABASE_TYPE} is up!"
fi


SETTINGS_LOCAL=$REVIEWBOARD_SITEDIR/conf/settings_local.py

if [ -e $SETTINGS_LOCAL ]; then
    # The site directory exists. Upgrade it.
    rb-site upgrade \
        --copy-media \
        $REVIEWBOARD_SITEDIR

    # Install any missing extension media files.
    rb-site manage $REVIEWBOARD_SITEDIR \
        install-extension-media -- --force
else
    # The site directory does not exist. Create a new one.
    echo "Creating initial Review Board site directory..."
    rb-site install \
        --noinput \
        --copy-media \
        --admin-email=admin@example.com \
        --admin-password=admin \
        --admin-user=admin \
        --allowed-host=127.0.0.1 \
        --cache-info="$MEMCACHED_SERVER" \
        --cache-type=memcached \
        --company="$COMPANY" \
        --db-host="$DATABASE_SERVER" \
        --db-name="$DATABASE_NAME" \
        --db-user="$DATABASE_USERNAME" \
        --db-pass="$DATABASE_PASSWORD" \
        --db-type="$DATABASE_TYPE" \
        --domain-name="$DOMAIN" \
        --web-server-port=80 \
        --web-server-type=apache \
        $REVIEWBOARD_SITEDIR

    # Force logging all content to stdout.
    echo "LOGGING_TO_STDOUT = True" >> $SETTINGS_LOCAL

    if [ "$ENABLE_POWERPACK" == "yes" ]; then
        rb-site manage $REVIEWBOARD_SITEDIR \
            enable-extension rbpowerpack.extension.PowerPackExtension
    fi
fi

chown -R reviewboard:reviewboard \
    $REVIEWBOARD_SITEDIR/data \
    $REVIEWBOARD_SITEDIR/htdocs/media/ext \
    $REVIEWBOARD_SITEDIR/htdocs/media/uploaded \
    $REVIEWBOARD_SITEDIR/htdocs/static/ext \
    $REVIEWBOARD_SITEDIR/logs \
    $REVIEWBOARD_SITEDIR/tmp


echo "Running server..."
exec gosu reviewboard "$@"
