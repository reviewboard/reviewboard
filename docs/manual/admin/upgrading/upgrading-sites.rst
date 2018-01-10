.. _upgrading-sites:

===============
Upgrading Sites
===============

Any time Review Board has been upgraded, each site must also be upgraded.
Upgrading serves several key tasks:

* Performs database updates and migrations
* Rebuilds missing parts of the directory structure
* Updates the local copies or links to the Review Board media files

If you don't perform an upgrade, your site may appear broken.

Before upgrading, we highly recommend backing up your database, in case
something goes wrong. You can also enable read-only mode from the
:ref:`general-settings` page to alert your users.

To begin a site upgrade, run::

    $ rb-site upgrade /path/to/site

This will display some output in the console. When it's finished, restart
your web server and your site should be ready.


Troubleshooting Upgrades
------------------------

It's possible after a site upgrade that cached data may be out of date,
either in memcached or in the users' browsers. If you do notice problems,
try restarting memcached, and tell the users to clear their browser cache.
