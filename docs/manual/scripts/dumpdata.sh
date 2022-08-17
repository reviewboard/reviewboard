#!/bin/sh

./docsmanage.py dumpdata \
    -e auth.Permission \
    --indent=4 \
    auth \
    accounts \
    attachments \
    changedescs \
    diffviewer \
    djblets_extensions \
    hostingsvcs \
    notifications \
    oauth2_provider \
    oauth \
    reviews \
    scmtools \
    site \
    webapi \
    > fixtures/initial_data.json
