================
Optimizing MySQL
================

MySQL has a few options for tuning performance that can greatly speed up
Review Board's queries.


Query Caching
=============

Query caching allows MySQL to store the results of previous queries so that
they can be returned quickly the next time the query is performed. This can
be very beneficial on many pages, particularly review requests and the
dashboard.

The amount of memory available for query caching can be configured. It's
good to give a minimum of 20MB, but larger query caches will allow more
data to be stored.

To enable query caching, first open the MySQL config file. On Linux, this is
located at :file:`/etc/my.cnf`. On Windows, this may be named :file:`my.ini`.

All cache settings are in the ``[mysqld]`` section of the file.

``query_cache_type`` needs to be set to 1 to enable caching.

``query_cache_size`` is the size of the cache. This can be in bytes, or you
can use a ``M`` suffix to specify the amount of megabytes.

``query_cache_limit`` is the maximum size of an individually cached query.
Queries over this size won't go into the cache. This is also in bytes, or
megabytes with the ``M`` suffix. 1MB is a safe bet.

To enable query caching with 64MB, set::

    [mysqld]
    query_cache_type = 1
    query_cache_size = 64M
    query_cache_limit = 1M


MySQL Packet Size
=================

Viewing very large diffs can cause a problem where queries exceed the default
MySQL packet size (16MB).

This can be changed through the ``max_allowed_packet`` configuration variable.
You can set this on the database by editing :file:`/etc/my.cnf` and setting::

    [mysqld]
    max_allowed_packet=32M

You can set this value to any number you need, in megabytes.

If you only need to set this for a session, such as when dumping your
database, you can instead pass this on the command line::

    $ mysqldump --max-allowed-packet=32M

Diffs larger than a megabyte are nearly impossible for ordinary humans
to review and can slow down the server in other ways. Reviews with such large
diffs are almost always caused by some intermediate build step such as
auto-generated or emitted code. A better solution is to be more careful about
posting reviews that may contain these sorts of files.
