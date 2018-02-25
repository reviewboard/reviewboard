.. program:: rb-site

================
The rb-site Tool
================

Overview
========

Most of the work of installing and managing a Review Board site is done for
you by a tool bundled with Review Board called :command:`rb-site`.

:command:`rb-site` has three main commands:

* install_
* upgrade_
* manage_

These will be discussed in detail in the following sections.

:command:`rb-site` always requires a command as the first argument and a site
directory as the second. Some commands may accept additional arguments.


Global Options
==============

.. cmdoption:: --version

   Shows the version number and exits.

.. cmdoption:: -h, --help

   Shows the help for the program and exits.

.. cmdoption:: --console

   Forces use of the console UI for any interaction.

.. cmdoption:: -d, --debug

   Displays debug output in the console.


.. _install:
.. program:: rb-site install

rb-site install
===============

Installs a new Review Board site. This will ask a series of questions and
will populate a tree for the website, as well as generate configuration
files.

If :command:`rb-site` is run in an X11 environment with `GTK+`_, then
this will present a graphical wizard for the questions. Otherwise, this
will ask in the console.

This takes a directory as the first parameter. For example::

    $ rb-site install /path/to/site

See :ref:`creating-sites` for more information.


.. _`GTK+`: https://www.gtk.org/


Options
-------

.. cmdoption:: --copy-media

   Copies media files to the site directory. By default, media files and
   directories are symlinked. This option is implied on Windows.

.. cmdoption:: --noinput

   Runs non-interactively, using configuration provided through command
   line options.

.. cmdoption:: --domain-name=<DOMAIN_NAME>

   The full domain name of the site, excluding the ``http://`` port or
   path. For example, ``reviews.example.com``

.. cmdoption:: --site-root=<SITE_ROOT>

   The path of the site, relative to the domain. This should end with a
   trailing ``/``. For example, ``/`` or ``/reviews/``.

.. cmdoption:: --media-url=<MEDIA_URL>

   The URL containing the media files. This should end with a trailing
   ``/``. For example, ``/media/`` or ``http://media.example.com/``.

.. cmdoption:: --db-type=<DB_TYPE>

   The database type. This should be one of:

   * ``mysql``
   * ``postgresql``
   * ``sqlite3``

.. cmdoption:: --db-name=<DB_NAME>

   The database name (database file path for sqlite3).

.. cmdoption:: --db-user=<DB_USER>

   The username used for connecting to the database (not used for sqlite3).

.. cmdoption:: --db-pass=<DB_PASS>

   The password used for connecting to the database (not used for sqlite3).

.. cmdoption:: --cache-type=<CACHE_TYPE>

   The cache server type. This should be one of:

   * ``memcached``
   * ``file``

.. cmdoption:: --cache-info=<CACHE_INFO>

   The detailed cache information. This is dependent on the cache type
   used.

   For ``memcached``, this should be a connection string (such as
   ``memcached://localhost:11211/``.

   For ``file``, this should be the path to a cache directory that the
   web server can write to.

.. cmdoption:: --web-server-type=<WEB_SERVER_TYPE>

   The type of web server that will run the site. This should be one of:

   * ``apache``
   * ``lighttpd``

.. cmdoption:: --python-loader=<PYTHON_LOADER>

   The type of Python loader.  This should be one of:

   * ``modpython``
   * ``fastcgi``

   For ``lighttpd``, the only choice is ``fastcgi``.

.. cmdoption:: --admin-user=<ADMIN_USER>

   The username for the new site administrator account.

.. cmdoption:: --admin-password=<ADMIN_PASSWORD>

   The password for the new site administrator account.

.. cmdoption:: --admin-email=<ADMIN_EMAIL>

   The e-mail address for the new site administrator account.


.. _upgrade:
.. program:: rb-site upgrade

rb-site upgrade
===============

Upgrades an existing site installation. This will update the media trees
and upgrade the database.

This must be performed every time Review Board is upgraded.

This takes a directory as the first parameter. For example::

    $ rb-site upgrade /path/to/site

See :ref:`upgrading-sites` for more information.


Options
-------

.. cmdoption:: --no-db-upgrade

   Prevents an upgrade and evolution of the database.


.. _manage:
.. program:: rb-site manage

rb-site manage
==============

Performs management commands on a site.

This is an advanced command that wraps the Django_ :command:`manage.py`
command. It takes a path to the site, a manage subcommand, and optional
parameters (following a ``--``).

For example::

    $ rb-site manage /path/to/site shell
    $ rb-site manage /path/to/site index -- --full


You can see the list of manage subcommands by running::

    $ rb-site manage /path/to/site help


For more information, and some useful subcommands, see
:ref:`management-commands`.


.. _Django: https://www.djangoproject.com/
