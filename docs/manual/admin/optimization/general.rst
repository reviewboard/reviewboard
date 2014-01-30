=========================
General Optimization Tips
=========================

Hardware
========

Review Board itself is heavily CPU and network-bound. While generating
side-by-side diffs, Review Board will fetch files from your repository,
patch them, and perform analysis on the files.

The process can be CPU-heavy, and potentially memory-heavy.


CPU
---

Giving the server more cores/CPUs will help with performance. 2 cores should
be a minimum. We recommend at least 4, if you can spare it.


Memory
------

2GB of RAM should be a bare minimum for a server. The more RAM you can spare,
the better.

Review Board, your database, and particularly memcached will all function
better with more RAM.

In particular, you want to set aside a lot of RAM for memcached. See
:ref:`optimizing-memcached` for more information.


Disks
-----

The database will benefit greatly from faster disks. 7200RPM should be a
minimum.


Multi-Server Strategy
=====================

Review Board is known to work well on large deployments with thousands of
users using a single physical or virtual machine However, in order to really
tune performance, you may want to consider a multi-server strategy.

One of the best ways to improve performance is to separate your deployment
into multiple servers. You can put memcached, your web server, and your
database server all on different machines and it will continue to work.


Database
--------

The first piece to split up is the database. Databases are heavily I/O-bound,
and generally need lots of memory in order to cache data for quicker access.
By moving a database onto its own server, you end up freeing a lot of disk
I/O and memory. This not only speeds up the database, but will speed up
all other services as well.


Memcached
---------

Memcached works entirely out of RAM, using no I/O and very little CPU.
It's less important to split this out initially, but it can be split onto
multiple machines, particularly if you need to increase your cache size but
are limited by how much RAM you can put in each system.

Review Board can be configured to provide a list of memcached servers.
Simply change your :ref:`cache settings <cache-settings>` to specify a list
of servers. For example, ``server1:11211;server2:11211``.


Web Server
----------

The web server can be split onto multiple machines, which increases the
number of clients that can access Review Board at once, and increase how
many diffs can be generated at once.

Diff generation is performed on the web server, and will therefore be scaled
out along with the web server.

.. note::

   If you want to scale out your web server, be aware of a couple important
   changes you need to make to your configuration.

   You will need to make sure your :file:`{sitedir}/htdocs/media/` directory
   is shared across all web server instances, or that you're using Amazon S3
   for your media.

   You will also need to ensure that your :file:`{sitedir}/data/` directory
   is shared across all instances. This is mainly due to each server needing
   access to your SSH keys.
