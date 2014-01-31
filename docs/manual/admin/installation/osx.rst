=============================
Installing on Mac OS X Server
=============================

By and large, the :ref:`Linux installation instructions <installation-linux>`
also work on Mac OS X Server. This document will serve to illustrate a couple
small differences.


Configuring Memcached start-up
==============================

To set up memcached to start on boot, use the following command::

    $ sudo launchctl load -w /System/Library/LaunchDaemons/com.danga.memcached.plist
