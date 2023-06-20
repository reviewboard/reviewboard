:tocdepth: 3

.. _management-commands:

============================
Advanced Management Commands
============================

:command:`rb-site` provides a ``manage`` command for certain management tasks.
The format for the commands is always:

.. code-block:: console

   $ rb-site manage /path/to/sitedir command-name parameters


The management commands that administrators are most likely to use are
explained in detail in the following sections.

To get a complete list of all management commands, run:

.. code-block:: console

   $ rb-site manage /path/to/sitedir help

And to retrieve information on a specific management command:

.. code-block:: console

   $ rb-site manage /path/to/sitedir help command-name


.. _management-commands-configuration:

Configuration Commands
======================

These commands are used to inspect or update your Review Board configuration

* :rb-management-command:`get-siteconfig`: Retrieve a value from configuration
* :rb-management-command:`set-siteconfig`: Set a configuration value
* :rb-management-command:`list-siteconfig`: List the current configuration
* :rb-management-command:`resolve-check`: Resolve a required system check for
  an upgrade


.. rb-management-command:: get-siteconfig
.. program:: get-siteconfig

``get-siteconfig`` - Get a Configuration Value
----------------------------------------------

This command displays the value for a Review Board configuration setting. It
can be useful for automation scripts.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir get-siteconfig --key <KEY>

The value will be outputted directly.


Options
~~~~~~~

.. option:: --key KEY

   The name of the configuration key to fetch.


.. rb-management-command:: list-siteconfig
.. program:: list-siteconfig

``list-siteconfig`` - List Configuration Settings
-------------------------------------------------

This command lists all stored configuration settings as JSON data. This is
useful for inspecting the current settings and finding keys to change.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir list-siteconfig


.. rb-management-command:: resolve-check
.. program:: resolve-check

``resolve-check`` - Resolve System Check
----------------------------------------

This command is used to resolve certain system checks that can occur during
installation/upgrade. These are steps that are required by Review Board but
cannot be performed automatically.

Review Board will tell you when you need to run this command, and what
parameters to provide.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir resolve-check <CHECK_NAME>

The status or error will be shown.


.. rb-management-command:: set-siteconfig
.. program:: set-siteconfig

``set-siteconfig`` - Set a Configuration Value
----------------------------------------------

This command sets a new value for an existing configuration setting. It can be
useful for automation scripts.

.. note::

   Not all settings can be changed through this command.

   Some settings require using the :rb-management-command:`shell` command,
   and should only be changed if directed by `Beanbag support`_.


.. _management-commands-data:

Data Commands
=============

These commands help with your site's data management.

* :rb-management-command:`condensediffs`:
  Upgrade diff storage and condense the diffs in the database. This can reduce
  database size when upgrading Review Board.

* :rb-management-command:`import-ssh-keys`:
  Import the host's SSH keys into the database, for shared SSH storage.
  This requires `Power Pack`_.


.. rb-management-command:: condensediffs
.. program:: condensediffs

``condensediffs`` - Condense/Upgrade Diff Storage
-------------------------------------------------

Review Board occasionally introduces new and improved ways of storing diffs,
offering new features or reducing storage requirements. This command is used
to move any older diffs into the latest type of diff storage.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir condensediffs [<options>]


Options
~~~~~~~

.. option:: --max-diffs COUNT

   Specifies a maximum number of migrations to perform. This is useful if
   you have a lot of diffs to migrate and want to do it over several
   sessions.

.. option:: --no-progress

   Don't show progress information or totals while migrating. You might want
   to use this if your database is taking too long to generate total migration
   counts.

.. option:: --show-counts-only

   Show the number of diffs expected to be migrated, without performing a
   migration.


.. rb-management-command:: import-ssh-keys
.. program:: import-ssh-keys

``import-ssh-keys`` - Import SSH Keys
-------------------------------------

This is used to import any existing SSH keys into Power Pack's distributed
SSH key storage, used by many types of repositories.

Distributed SSH keys are shared across all Review Board servers in your
network serving the same site. It's useful for Docker environments and other
multi-server setups.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir import-ssh-keys

This will automatically import the keys into storage and then exit.

.. note::

   `Power Pack`_ must be installed and licensed in order to run this command
   or use distributed SSH keys.


.. _management-commands-debugging:

Debugging Commands
==================

These commands give you some insight into your Review Board installation,
helping you inspect information or perform certain commands.

* :rb-management-command:`dbshell`:
  Open a database shell using your standard database tools (e.g.,
  :command:`mysql` or :command:`psql`).

* :rb-management-command:`find-large-diffs`:
  Scan the database looking for very large diffs that may be contributing to
  performance problems.

* :rb-management-command:`shell`:
  Open a Python shell in the Review Board environment.


.. rb-management-command:: dbshell
.. program:: dbshell

``dbshell`` - Open a Database Shell
-----------------------------------

This command opens a database shell using Review Board's credentials. This can
be useful for advanced debugging and database management.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir dbshell

You can then issue SQL statements with the same permissions available to your
Review Board server.

.. danger::

   This will have direct access to your database. If you're not careful, this
   can lead to data loss or other problems.

   We recommend using this only if you're experienced and have a backup
   of your database, or are guided by `Beanbag support`_.


.. rb-management-command:: find-large-diffs
.. program:: shell
.. _management-command-find-large-diffs:

``find-large-diffs`` - Find Very Large Diffs
--------------------------------------------

.. program:: find-large-diffs

.. versionadded:: 5.0.3

When :ref:`troubleshooting performance problems
<troubleshooting-performance>`, it can be helpful to scan for large diffs
that may have been uploaded to the database.

This command will output in CSV format, for processing and analysis.

Results from this command will often be requested when `contacting support`_
about performance problems.

To check for large diffs from the past N days, run:

.. code-block:: console

   $ rb-site manage /path/to/sitedir find-large-diffs \
         --num-days=<N>

To check for a range of review request IDs:

.. code-block:: console

   $ rb-site manage /path/to/sitedir find-large-diffs \
         --start-id=<ID> --end-id=<ID>

For example:

.. code-block:: console

   $ rb-site manage /path/to/sitedir find-large-diffs --num-days=100
   This will scan 35 review requests. Continue? [Y/n] y
   Review Request ID,Last Updated,User ID,Max Files,Max Diff Size,Max Parent Diff Size,Diffset ID for Max Files,Diffset ID for Max Diff Size,Diffset ID for Max Parent Diff Size
   325,2023-03-22 02:54:45.411235+00:00,1,122,101288,0,514,514,0
   328,2023-03-09 12:21:57.841850+00:00,1,14,63378,160718,517,517,517
   334,2023-04-23 01:36:54.422582+00:00,1,6,70384,108192,535,535,535
   337,2023-09-14 22:54:14.637025+00:00,1,5,107403,0,543,544,0


The following options are available to customize your scan:

.. option:: --min-size <MIN_SIZE_BYTES>

   Minimum diff or parent diff size to include in a result.

   A review request is included if a diff meets :option:`--min-size` or
   :option:`--min-files`.

   Defaults to ``100000`` (100KB).

.. option:: --min-files <MIN_FILES>

   Minimum number of files to include in a result.

   A review request is included if a diff meets :option:`--min-size` or
   :option:`--min-files`.

   Defaults to ``50``.

.. option:: --start-id <ID>

   Starting review request ID for the scan.

   Either :option:`--start-id` or :option:`--num-days` must be specified.

.. option:: --end-id <ID>

   Last review request ID for the scan.

   Defaults to the last ID in the database.

.. option:: --num-days <DAYS>

   Number of days back to scan for diffs.

   Either :option:`--start-id` or :option:`--num-days` must be specified.

.. option:: --noinput, --no-input

   Disable prompting for confirmation before performing the scan.


.. rb-management-command:: shell
.. program:: shell

``shell`` - Open a Command Shell
--------------------------------

Power users who wish to run Python commands against an installed Review
Board server can do so with the ``shell`` management command. This can be
useful if you're a developer looking to test some code against Review
Board.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir shell

You can then run Python code within the context of Review Board.

.. danger::

   This will have direct access to your database and Review Board system
   files. If you're not careful, this can lead to data loss or other
   problems.

   We recommend using this only if you're experienced and have a backup
   of your database, or are guided by `Beanbag support`_.


.. _management-commands-extensions:

Extension Commands
==================

These commands let you manage your installed extensions without logging into
Review Board. These can be useful if you're encountering problems starting
up due to a problem with an extension.

* :rb-management-command:`disable-extension`:
  Disable an extension.

* :rb-management-command:`enable-extension`:
  Enable an extension.

* :rb-management-command:`list-extensions`:
  List all installed and available extensions.


.. rb-management-command:: disable-extension
.. program:: disable-extension

``disable-extension`` - Disable Extension
-----------------------------------------

This disables one or more extensions. It's the equivalent of going into
:guilabel:`Administration UI -> Extensions` and disabling extensions, and
can be useful for automation scripts.

See :ref:`admin-ui-manage-extensions`.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir disable-extension EXTENSION_ID [...]

One or more extension IDs can be provided. See
:rb-management-command:`list-extensions` to see the list of IDs.


.. rb-management-command:: enable-extension
.. program:: enable-extension

``enable-extension`` - Enable Extension
---------------------------------------

This enables one or more extensions. It's the equivalent of going into
:guilabel:`Administration UI -> Extensions` and enabling extensions, and
can be useful for automation scripts.

See :ref:`admin-ui-manage-extensions`.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir enable-extension EXTENSION_ID [...]

One or more extension IDs can be provided. See
:rb-management-command:`list-extensions` to see the list of IDs.


.. rb-management-command:: list-extensions
.. program:: list-extensions

``list-extensions`` - List Extensions
-------------------------------------

Lists the extensions registered with Review Board. The name, enabled status,
and extension ID will be shown for each extension.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir list-extensions [<options>]


Options
~~~~~~~

.. option:: --enabled

   Filter the list to enabled extensions only.


.. _management-commands-packages:

Package Management/Runtime Commands
===================================

.. versionadded:: 5.0.5

These commands help you manage packages in your Review Board installation,
and work with the correct version of Python. They're recommended over using
the corresponding system-level commands.

* :rb-management-command:`pip`:
  Run the correct :command:`pip` package management tool for Review Board.

* :rb-management-command:`python`:
  Run the correct :command:`python` interpreter for Review Board.


.. rb-management-command:: pip
.. program:: pip

``pip`` - Python Package Tool
-----------------------------

.. versionadded:: 5.0.5

This wraps around the correct version of :command:`pip` for your Review Board
environment. It's used for installing or managing packages for Review Board.

See the `pip documentation`_ for usage instructions.


.. _pip documentation: https://pip.pypa.io/


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir pip <command> [<options>]

To install a package:

.. code-block:: console

   $ rb-site manage /path/to/sitedir pip install <packagename>

To upgrade a package:

.. code-block:: console

   $ rb-site manage /path/to/sitedir pip install -U <packagename>

To uninstall a package:

.. code-block:: console

   $ rb-site manage /path/to/sitedir pip uninstall <packagename>

To show information on a package:

.. code-block:: console

   $ rb-site manage /path/to/sitedir pip show <packagename>

To list installed packages:

.. code-block:: console

   $ rb-site manage /path/to/sitedir pip list


.. rb-management-command:: python
.. program:: python

``python`` - Python Interperter
-------------------------------

.. versionadded:: 5.0.5

This wraps around the correct version of :command:`python` for your Review
Board environment. It's used for executing Python code in your Review Board
environment.

This differs from :rb-management-command:`shell` in that Python code *will
not* run within the Review Board process.

.. _pip documentation: https://pip.pypa.io/


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir python [<options>]


.. _management-commands-search:
.. _search-indexing-management-command:

Search Commands
===============

Review Board installations with indexed search enabled must periodically
index the database. This is done through the following commands:

* :rb-management-command:`clear_index`:
  Clear the search index.

* :rb-management-command:`rebuild_index`:
  Rebuild the search index from scratch.

* :rb-management-command:`update_index`:
  Create or update the configured search index.

A sample ``crontab`` file is available at :file:`conf/cron.conf` under
an installed site directory.

The generated search index will be placed in the
:ref:`search index directory <search-index-directory>` specified in the
:ref:`general-settings` page. By default, this should be the
:file:`search-index` directory in your site directory.

.. note::

   If you have :ref:`on-the-fly indexing <search-indexing-methods>` enabled,
   the search index should stay up-to-date automatically without running
   :rb-management-command:`update_index`.


.. rb-management-command:: clear_index
.. program:: clear_index

``clear_index`` - Clear the Search Index
----------------------------------------

This command will erase the current search index. A rebuild will be required
before any new searches can be conducted.

By default, this will prompt for confirmation before clearing the index.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir clear_index [<options>]n


Options
~~~~~~~

.. option:: --noinput

   The search index will be cleared without prompting for confirmation.


.. rb-management-command:: rebuild_index
.. program:: rebuild_index

``rebuild_index`` - Rebuild the Search Index
--------------------------------------------

This command will erase the current search index and then rebuild it from
scratch. This can take some time.

By default, this will prompt for confirmation before clearing the index.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir rebuild_index [<options>]


Options
~~~~~~~

.. option:: --noinput

   The rebuild will happen without prompting for confirmation.

.. option:: -b BATCH_SIZE, --batch-size BATCH_SIZE

   The number of items to index per batch.

   This is an advanced option. The default is usually safe.

.. option:: -k NUM_WORKERS, --workers NUM_WORKERS

   The number of worker processes to run to perform the indexing. This can
   reduce the time needed to index the database.

.. option:: -t MAX_RETRIES, --max-retries MAX_RETRIES

   The number of times to retry a write to the search index if an error
   (such as a communication error) occurs.


.. rb-management-command:: update_index
.. program:: update_index

``update_index`` - Update the Search Index
------------------------------------------

The :command:`update_index` management command will create or update the
current search index with any new content. It can be run periodically.

By default, this will prompt for confirmation before clearing the index.

If :ref:`on-the-fly indexing <search-indexing-methods>` is enabled, this
command is not required, but can help with catching objects that may have
failed to write due to temporary failures in the search backend.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir update_index -r -a <hours> [<options>]

``<hours>`` is the number of hours back to look for new items to include in
the search index.

This command should be run periodically in a task scheduler, such as
:command:`cron` on Linux.

We recommend using ``-a 1`` and scheduling the command to run every 10
minutes. This helps keep your index up-to-date while also allowing for some
buffer room in case of a temporary outage or upgrade.

All other options should be considered optional.


Options
~~~~~~~

.. option:: --noinput

   The rebuild will happen without prompting for confirmation.

.. option:: -a HOURS, --age HOURS

   The number of hours back to consider an item new. We recommend ``1``.

.. option:: -m MINUTES, --minutes MINUTES

   The number of minutes back to consider an item new.

.. option:: -s START_DATE, --start START_DATE

   The starting date range for any objects considered for indexing. This
   must be in :term:`ISO8601 format`.

.. option:: -e END_DATE, --end END_DATE

   The ending date range for any objects considered for indexing. This
   must be in :term:`ISO8601 format`.

.. option:: -r, --remove

   Remove objects from the index that are no longer present in the database.

.. option:: -b BATCH_SIZE, --batch-size BATCH_SIZE

   The number of items to index per batch.

   This is an advanced option. The default is usually safe.

.. option:: -k NUM_WORKERS, --workers NUM_WORKERS

   The number of worker processes to run to perform the indexing. This can
   reduce the time needed to index the database.

.. option:: -t MAX_RETRIES, --max-retries MAX_RETRIES

   The number of times to retry a write to the search index if an error
   (such as a communication error) occurs.


.. _management-commands-users:

User Management Commands
========================

These commands can help with managing users and API tokens on your server:

* :rb-management-command:`changepassword`:
  Change the password for a user.

* :rb-management-command:`createsuperuser`:
  Create a new Review Board administrator.

* :rb-management-command:`invalidate-api-tokens`:
  Invalidate API tokens for one or more users.


.. rb-management-command:: changepassword
.. program:: changepassword

``changepassword`` - Change a User's Password
---------------------------------------------

This command will change an existing user's password to a newly-supplied one,
helping them get back into the system if they're unable to reset their own
password.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir changepassword <username>

This will prompt for a new password for the user.


.. rb-management-command:: createsuperuser
.. program:: createsuperuser
.. _creating-a-super-user:

``createsuperuser`` - Create a Super User
-----------------------------------------

It is possible to create a new super user account without using the
website. This can be important if the main super user account is for
whatever reason disabled or if the login information is lost.


Usage
~~~~~

.. code-block:: console

   $ rb-site manage /path/to/sitedir createsuperuser

This will prompt for the username and password of the account. You must
specify a user that doesn't already exist in the database. Once this is
finished, you should be able to log in under the new account and fix any
problems you have.


Options
~~~~~~~

.. option:: --email

   The optional e-mail address for the new user. If specified, you won't be
   prompted for one.

.. option:: --username

   The optional username for the new user. If specified, you won't be
   prompted for one.


.. rb-management-command:: invalidate-api-tokens
.. program:: invalidate-api-tokens
.. _management-command-invalidate-api-tokens:

``invalidate-api-tokens`` - Invalidate API Tokens
-------------------------------------------------

.. versionadded:: 5.0

In the event of security issues, you can invalidate :ref:`API tokens
<webapi2.0-api-tokens>` for specific users or all users on your server.


Usage
~~~~~

To invalidate for specific users:

.. code-block:: console

   $ rb-site manage /path/to/sitedir invalidate-api-tokens <user1> <user2>...

To invalidate the tokens of all users, run:

.. code-block:: console

   $ rb-site manage /path/to/sitedir invalidate-api-tokens --all

You can also supply a reason for invalidating the tokens by passing the
``--reason <reason>`` argument.


Options
~~~~~~~

.. option:: -a, --all

   Invalidate all tokens on the server.

.. option:: -r REASON, --reason REASON

   Store a reason the token was invalidated. This will show up on the token
   information.


.. _Beanbag support: https://www.reviewboard.org/support/
.. _contacting support: https://www.reviewboard.org/support/
.. _Power Pack: https://www.reviewboard.org/powerpack/
