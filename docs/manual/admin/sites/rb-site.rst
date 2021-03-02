.. program:: rb-site

================
The rb-site Tool
================

Overview
========

Most of the work of installing and managing a Review Board site is done for
you by a tool bundled with Review Board called :command:`rb-site`.

:command:`rb-site` has three main commands:

* :ref:`rb-site-install`
* :ref:`rb-site-upgrade`
* :ref:`rb-site-manage`

These will be discussed in detail in the following sections.

:command:`rb-site` always requires a command as the first argument and a site
directory as the second. Some commands may accept additional arguments.


Global Options
==============

.. option:: --console

   Forces use of the console UI for any interaction.

.. option:: -d, --debug

   Displays debug output in the console.

.. option:: -h, --help

   Shows the help for the program and exits.

.. option:: --no-color

   Disable all color output.

   .. versionadded:: 4.0

.. option:: --version

   Shows the version number and exits.


.. _rb-site-install:

rb-site install
===============

.. program:: rb-site install

Installs a new Review Board site. This will ask a series of questions and
will populate a tree for the website, as well as generate configuration
files.

This takes a directory as the first parameter. For example::

    $ rb-site install /path/to/site

See :ref:`creating-sites` for more information.


Options
-------

.. option:: --admin-email=<ADMIN_EMAIL>

   The e-mail address for the new site administrator account.

.. option:: --admin-password=<ADMIN_PASSWORD>

   The password for the new site administrator account.

.. option:: --admin-user=<ADMIN_USER>

   The username for the new site administrator account.

.. option:: --allowed-host=<HOSTNAME>

   An additional hostname or IP address that can be used to reach the
   server. This option can be provided multiple times.

   Any request made to the server that isn't provided in the allowed host
   list, or in :option:`--domain-name`, will be blocked.

   .. versionadded:: 4.0

.. option:: --advanced

   Prompt for advanced options during installation.

.. option:: --cache-info=<CACHE_INFO>

   The detailed cache information. This is dependent on the cache type
   used.

   For ``memcached``, this should be a connection string (such as
   ``memcached://localhost:11211/``.

   For ``file``, this should be the path to a cache directory that the
   web server can write to.

.. option:: --cache-type=<CACHE_TYPE>

   The cache server type. This should be one of:

   * ``memcached``
   * ``file``

.. option:: --company=<COMPANY>

   The name of the company or organization that owns the Review Board server.
   This is used for support purposes.

.. option:: --copy-media

   Copies media files to the site directory. By default, media files and
   directories are symlinked. This option is implied on Windows.

.. option:: --db-host=<HOSTNAME>

   The hostname running the database server (not used for sqlite3).

.. option:: --db-name=<DB_NAME>

   The database name (database file path for sqlite3).

.. option:: --db-pass=<DB_PASS>

   The password used for connecting to the database (not used for sqlite3).

.. option:: --db-type=<DB_TYPE>

   The database type. This should be one of:

   * ``mysql``
   * ``postgresql``
   * ``sqlite3``

.. option:: --db-user=<DB_USER>

   The username used for connecting to the database (not used for sqlite3).

.. option:: --domain-name=<DOMAIN_NAME>

   The full domain name of the site, excluding the ``http://`` port or
   path. For example, ``reviews.example.com``

.. option:: --media-url=<MEDIA_URL>

   The URL containing the media files. This should end with a trailing
   ``/``. For example, ``/media/`` or ``http://media.example.com/``.

.. option:: --opt-in-support-data

   Opt into sending data and stats to help with support.

   .. versionadded:: 4.0

.. option:: --noinput

   Runs non-interactively, using configuration provided through command
   line options.

.. option:: --secret-key=<SECRET_KEY>

   A specific value to use for the site's Secret Key. All site installations
   using the same database *must* use the same Secret Key.

   This is recommended if automating installs using Docker or another
   service.

   .. versionadded:: 4.0

.. option:: --settings-local-template=<PATH>

   A custom template file used to generate the site's
   :file:`conf/settings_local.py` file.

   .. versionadded:: 4.0

.. option:: --site-root=<SITE_ROOT>

   The path of the site, relative to the domain. This should end with a
   trailing ``/``. For example, ``/`` or ``/reviews/``.

.. option:: --sitelist=<PATH>

   The path to a global file used to store the list of installed site
   directories. This is optional, and used for automating upgrades across
   multiple site directories.

.. option:: --web-server-type=<WEB_SERVER_TYPE>

   The type of web server that will run the site. This should be one of:

   * ``apache``
   * ``lighttpd``


.. _rb-site-upgrade:

rb-site upgrade
===============

.. program:: rb-site upgrade

Upgrades an existing site installation. This will update the media trees
and upgrade the database.

This must be performed every time Review Board is upgraded.

This takes a directory as the first parameter. For example::

    $ rb-site upgrade /path/to/site

See :ref:`upgrading-sites` for more information.


Options
-------

.. option:: --all-sites

   Upgrade all installed sites.

   See :option:`--sitelist`.

.. option:: --copy-media

   Copies media files to the site directory. By default, media files and
   directories are symlinked. This option is implied on Windows.

.. option:: --no-db-upgrade

   Prevents an upgrade and evolution of the database.

.. option:: --sitelist=<PATH>

   The path to a global file used to store the list of installed site
   directories. This is optional, and used for automating upgrades across
   multiple site directories.


.. _rb-site-manage:

rb-site manage
==============

.. program:: rb-site manage

Performs management commands on a site.

This allows commands provided by Review Board or extensions to be run
on your Review Board site. It takes a path to the site, a manage subcommand,
and optional parameters.

For example::

    $ rb-site manage /path/to/site shell
    $ rb-site manage /path/to/site index --full


You can see the common list of manage subcommands by running::

    $ rb-site manage --help

Or the full list of all management subcommands (some provided by Django_,
which may not be relevant to Review Board)::

    $ rb-site manage /path/to/site list-commands


For more information, and some useful subcommands, see
:ref:`management-commands`.


.. _Django: https://www.djangoproject.com/
