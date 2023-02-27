.. _management-commands:

============================
Advanced Management Commands
============================

:command:`rb-site` provides a ``manage`` command for certain management tasks.
The format for the commands is always::

    $ rb-site manage /path/to/site command-name -- parameters


The management commands that administrators are most likely to use are
explained in detail in the following sections.

To get a complete list of all management commands, run::

    $ rb-site manage /path/to/site help

And to retrieve information on a specific management command::

    $ rb-site manage /path/to/site help command-name


.. _search-indexing-management-command:

Search Indexing
---------------

Review Board installations with indexed search enabled must periodically
index the database. This is done through the ``rebuild_index`` and
``update_index`` management commands (The ``index`` command will be
deprecated in a future release).

To perform a full index::

    $ rb-site manage /path/to/site rebuild_index

To perform an index update::

    $ rb-site manage /path/to/site update_index -- -a <hours>

where ``<hours>`` is the number of hours since the last update. We recommend
using ``-a 1`` and run the update command every 10 minutes. This command should
be run periodically in a task scheduler, such as :command:`cron` on Linux.

A sample ``crontab`` entry is available at :file:`conf/cron.conf` under
an installed site directory.

The generated search index will be placed in the
:ref:`search index directory <search-index-directory>` specified in the
:ref:`general-settings` page. By default, this should be the
:file:`search-index` directory in your site directory.


.. _creating-a-super-user:

Creating a Super User
---------------------

It is possible to create a new super user account without using the
website. This can be important if the main super user account is for
whatever reason disabled or if the login information is lost.

To create a new super user account, run::

    $ rb-site manage /path/to/site createsuperuser


This will prompt for the username and password of the account. You must
specify a user that doesn't already exist in the database. Once this is
finished, you should be able to log in under the new account and fix any
problems you have.


Opening a Command Shell
-----------------------

Power users who wish to run Python commands against an installed Review
Board server can do so with the ``shell`` management command. This can be
useful if you're a developer looking to test some code against Review
Board.

To open a Python command shell, run::

    $ rb-site manage /path/to/site shell


Resetting Review Request Counters
---------------------------------

The counters in the Dashboard along the left-hand side, indicating the
number of review requests, can potentially be incorrect if changes were
made manually to the database or if there was an error while attempting to
save information to the database.

You can fix these counters by running::

    $ rb-site manage /path/to/site fixreviewcounts

This is done automatically when upgrading a site.


.. _management-command-invalidate-api-tokens:

Invalidating API Tokens
-----------------------

.. versionadded:: 5.0

The :ref:`API tokens <webapi2.0-api-tokens>` for a set of users can be
invalidated by running::

    $ rb-site manage /path/to/site invalidate-api-tokens <user1> <user2>...

To invalidate the tokens of all users, run::

    $ rb-site manage /path/to/site invalidate-api-tokens --all

You can also supply a reason for invalidating the tokens by passing the
``--reason <reason>`` argument.


.. _management-command-find-large-diffs:

Find Large Diffs
----------------

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


.. _contacting support: https://www.reviewboard.org/support/
