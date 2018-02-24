.. _administrator-dashboard:

=======================
Administrator Dashboard
=======================

The dashboard is the front page of the
:ref:`Administration UI <administration-ui>`. It provides convenient shortcuts
for common management tasks, some server information, and Review Board project
news updates.


Manage
======

The "Manage" section provides shortcuts to some common management tasks.
These are specifically links to add and edit the following entries in the
database:

* Users
* Review groups
* Default reviewers
* Repositories

Clicking the name will take you to a list of items for that type. For example,
clicking "Users" will show the list of all users. This is the same page that
you would get by clicking the same name in the
:ref:`Database Management <database-management>` section.

Clicking the "Add" link beside the name will let you quickly add a new item in
that section.

The number in parenthesis beside the name is the number of existing entries.


Server Information
==================

This section shows some basic information on the Review Board server:

* Review Board version
* Server Cache

Depending on your cache backend, The "Server Cache" link will be displayed.
This will take you to a page displaying detailed cache statistics.


Server Cache
------------

The Server Cache page shows information on the cache backend. When using
the memcached backend, statistics will be displayed for every registered
memcached server.

The statistics shown include:

* Memory usage (bytes)
* Number of keys in the cache
* Cache hits
* Cache misses
* Cache evictions
* Cache traffic (bytes in and out)
* Server uptime


.. _server-log:

Server Log
----------

If logging is enabled, the Server Log will show events that have happened on
the server since logging was enabled or logs were last rotated.

The log can be filtered by date ("Any date", "Today", "Past 7 days", or
"This month") and by log level ("Debug", "Info", "Warning", "Error",
"Critical", or "All").

The log can be particularly useful when encountering a problem with a
repository, mail server, or when having trouble accessing a page. The
information contained in the log file can be used by the Review Board
developers to help diagnose your problem.


News
====

Important Review Board news updates are displayed in the "News" section. A
snippet of each post is displayed, and the full post can be displayed by
clicking the post summary.

The upper-right of the news box contains links for viewing all the news items,
reloading the news box, and subscribing to an RSS feed for the news.

.. note:: If you're behind an HTTP Proxy, you may not see any news here.
          We will be adding HTTP Proxy support for this in a future update.
          In the meantime, you can visit the `Review Board News`_ page.

.. _`Review Board News`: https://www.reviewboard.org/news/
