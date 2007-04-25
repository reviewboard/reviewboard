#!/bin/sh

# ./manage.py runserver 0.0.0.0:80

# Run apache with given configuration
./manage.py runfcgi daemonize=false host=127.0.0.1 port=3033
