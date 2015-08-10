#!/bin/bash

echo ==============================
mkdir -p $DESTDIR/opt
virtualenv $DESTDIR/opt/anytask-env
source $DESTDIR/opt/anytask-env/bin/activate
cd /home/gebetix/package/anytask_packages/anytask
pip install -r requirements.txt
deactivate
mkdir -p $DESTDIR/opt
virtualenv $DESTDIR/opt/reviewboard-env
source $DESTDIR/opt/reviewboard-env/bin/activate
easy_install -U Djblets
easy_install -U RBTools
easy_install -U django_evolution
easy_install -U recaptcha-client
deactivate
