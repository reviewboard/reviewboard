===================================
Optimizing and Scaling Review Board
===================================

Review Board is heavily CPU and network-bound, and often depends on the
performance of other services inside our outside your network. For example:

1. **Database and memcached**

   Review Board depends on a healthy database. If your database server is
   slow to respond or acting up, or if your memcached service isn't running,
   the whole product will slow down.

2. :ref:`Source code repositories <repositories>`

   Posting changes for review or viewing diffs may cause Review Board to
   fetch files or metadata from your source code repositories, or trigger
   builds in CI services.

3. :ref:`Third-party service integrations <integrations>`

   If configured, Review Board may make periodic requests to communicate with
   these services.

4. :ref:`Authentication backends <authentication-method>`

   When logging in, Review Board may verify credentials on your configured
   authentication backend.

Performance can generally be improved by tweaking memcached, web server, or
Review Board settings. However, performance problems may originate with these
other services.

See :ref:`troubleshooting-performance` below if you encounter performance
problems with Review Board.


.. _recommended-hardware:

Recommended Hardware
====================

CPU / Cores
-----------

Review Board web servers and your database all benefit from multiple cores:

* **Memcached** can run on one core, and uses very little CPU.

* **Databases** benefit from multiple cores for data processing.

  You should allocate at least 2 cores for your database.

* **Review Board web servers** benefit from multiple cores for concurrent
  request handling.

  You should allocate at least 2 cores for your web server. Most web servers
  can be configured to spawn a specified number of processes and threads based
  on the number of cores you can allocate. You will need to tune these for
  optimal performance.

The database server and web server will both scale up with more cores. If your
deployment is under strain, you should consider `scaling out your deployment
<scaling-deployment>`_.

A small production server with all services running on the same machine can
generally get by with 2-4 cores.


RAM / Memory
------------

Review Board web servers, memcached, and database servers all benefit from
large amounts of RAM:

* **Memcached** is entirely RAM-based.

  Review Board heavily makes use of memcached to cache state. The more RAM
  you can dedicate, the more state can be reused across requests.

  We recommend at least 2GB dedicated for memcached.

* **Databases** need lots of RAM for computing and caching results.

  The more RAM your database has available, the better the database will
  perform, and therefore the better Review Board will perform.

  We recommend at least 2GB dedicated for your database. If your database is
  particularly large, you may need to increase this substantially.

* **Review Board web servers** need plenty of RAM to store and process state.

  We recommend at least 2GB dedicated for each web server.

A small production server with all services running on the same machine can
generally get by with 4GB of RAM.

More RAM is always better.

Actual recommendations vary based on the size of your deployment. You may
want to `scale out your deployment <scaling-deployment>`_ and prioritize
giving as much RAM to memcached and the database as possible.


Hard Disks / SSDs
-----------------

Databases perform better with faster hard drives. This directly translates
to better performance for Review Board.

We recommend using SSDs for your database, or 7200RPM spinning disks at a
minimum.


.. _optimizing-memcached:

Optimizing Memcached
====================

Memcached benefits from having lots of dedicated RAM.

By default, a memcached install usually only has around 32MB or 64MB
available, which is not enough for Review Board.

We recommend configuring memcached to have at least 2GB of RAM, if you can
comfortably spare it. Large or high-activity deployments may need more.

To increase the amount of memory available to memcached, specify the **value
in megabytes**. This differs based on the setup:

* On Debian_ or Ubuntu_, modify :file:`/etc/memcached.conf` and change ``-m``.

  For example, to configure 2GB:

  .. code-block:: shell

     -m 2048

* On `Red Hat Enterprise`_, Fedora_, or `CentOS Stream`_, modify
  :file:`/etc/sysconfig/memcached` and change ``CACHESIZE``.

  For example, to configure 2GB:

  .. code-block:: shell

     CACHESIZE="2048"

* On other setups (or if the file is missing), modify your ``memcached``
  launcher to set ``-m``.

  For example, to launch memcached with 2GB:

  .. code-block:: console

     $ memcached -m 2048


.. _setting-diff-limits:

Setting Diff Limits
===================

To keep your deployment running smoothly, we **strongly encourage** you to
set the following limits:

* **A maximum size of uploaded diffs.**

  We recommend setting this no higher than 2MB (2097152 bytes).

  Diffs any larger than this are usually the result of a bad revision range,
  auto-generated code, or third-party modules.

  Humans are incapable of providing meaningful reviews of diffs of this size
  or larger.

* **A maximum number of lines for syntax highlighting.**

  We recommend setting this no higher than 20,000 lines.

  The larger the file, the more work is required to syntax-highlight the
  file. If you're dealing with very large files, a limit can help.

These are both configured in :ref:`diffviewer-settings`.

.. important::

   If users report problems posting after setting a diff limit, that means
   limits are working.

   People may accidentally post a wrong revision range, leading to large
   diffs. Review Board tries to work around some bad revision ranges, so
   users may not even know they're doing this.

   If users begin to complain about hitting diff limits, **do not simply
   raise the limits**. Instead, diagnose the problem with the user. They may
   need to adjust their revision ranges or exclude auto-generated/third-party
   files from the change.


.. _scaling-deployment:

Scaling Your Deployment
=======================

Review Board is known to work well on large deployments with thousands of
users using a single physical or virtual machine.

However, in order to really tune performance, you may want to consider a
multi-server strategy.

One of the best ways to improve performance is to separate your deployment
into multiple physical servers, VMs, or cloud servers, giving each service
their own allocation of RAM and CPU.

Memcached, databases, and Review Board web servers all scale out to better
handle additional load.


Database
--------

Moving your database to a dedicated server can greatly improve performance.

Databases are heavily I/O-bound, and generally need lots of memory in order to
cache data for quicker access. By moving a database onto its own server, you
end up freeing a lot of disk I/O and memory.

This not only speeds up the database, but will speed up all other services as
well.

If scaling out your infrastructure, prioritize putting your database on
its own server.


Memcached
---------

Memcached works entirely out of RAM, using no I/O and very little CPU.

The more RAM you can dedicate to memcached, the better Review Board will
perform. To help with this, consider moving memcached to its own dedicated
server with plenty of RAM.

This is generally a requirement if you also plan to scale out your web
servers.

Review Board can be configured to provide a list of memcached servers.
Simply change your :ref:`cache settings <cache-settings>` to specify a list
of servers. For example, ``server1:11211;server2:11211``.

:ref:`Learn more about optimizing memcached <optimizing-memcached>`.


Web Servers
-----------

To help meet demand, you can configure multiple Review Board web servers,
all using the same Review Board database and memcached servers.

This can help increase the number of users that can access Review Board at
once. It can also increase performance for operations like diff generation,
repository communication, and various other actions.

If you want to scale out your web server, please be aware of a few things:

1. Either your :file:`{sitedir}/htdocs/media/` directory must be shared across
   all web server instances, or you must use a service like Amazon S3 for
   your media.

2. Your :file:`{sitedir}/data/` directory must be shared or kept in sync
   across all instances.

   This directory stores state like SSH keys and Perforce ticket files, which
   must be accessible to each server.

3. Keep your :term:`site directory` mostly local.

   Some companies have had success sharing the entire site directory over NFS,
   but this can sometimes prove unstable. We recommend having one site
   directory per server, and sharing only the directories above.


Load Balancer
-------------

You'll need to set up a load balancer in order to scale out your web servers.
Load balancers are responsible for handling incoming HTTP(s) requests and
sending them off to a web server for processing.

There are multiple solutions in this space, including:

* `Amazon Application Load Balancer (ALB)`_

  If you're deploying Review Board in the AWS cloud, Amazon's ALB is a good
  choice. It's an easy, reliable option that can dispatch requests to any
  number of Review Board web servers.

* HAProxy_

  HAProxy is a commonly-used, scalable load balancer that is known to work
  with Review Board.

  There are many ways you can configure HAProxy for your needs. The
  `HAProxy documentation`_ covers all configuration options, but you may
  want to start with this `HAProxy tutorial`_.

  We recommend enabling cookie-based or IP-based sticky sessions, which will
  ensure that users stay bound to a particular Review Board web server. This
  will help with caching and tracing user activity in log files.

* `Nginx Load Balancing`_

  Nginx can be used as a load balancer. This can be a simple option if you're
  familiar with Nginx.

  We recommend enabling ``ip-hash`` balancing, which will ensure that users
  stay bound to a particular Review Board web server. This will help with
  caching and tracing user activity in log files.


.. _Amazon Application Load Balancer (ALB):
   https://aws.amazon.com/elasticloadbalancing/application-load-balancer/
.. _HAProxy: https://www.haproxy.org/
.. _HAProxy documentation: http://docs.haproxy.org/
.. _HAProxy tutorial:
   https://www.haproxy.com/blog/haproxy-configuration-basics-load-balance-your-servers/
.. _Nginx Load Balancing: http://nginx.org/en/docs/http/load_balancing.html


.. _troubleshooting-performance:

Troubleshooting Performance Problems
====================================

This section will attempt to cover some common performance problems we've
seen over the years.

If you need help with diagnosing performance problems, `reach out to us for
support <support_>`_.

When there are problems (such as slowdown, timeouts, or high CPU usage), they
are usually symptoms of one of the following issues.

* **Users are trying to upload massive diffs, and diff limits aren't set.**

  Make sure you've followed our :ref:`diff limit recommendations
  <setting-diff-limits>` to avoid this problem.

  *This is very often the root cause of the issue.*

  To diagnose this, you can use the :ref:`find-large-diffs
  <management-command-find-large-diffs>` management command (available on
  Review Board 5.0.3 and higher):

  .. code-block:: console

     $ rb-site manage /path/to/sitedir find-large-diffs --num-days <DAYS>

  The script will look for any review requests with large diffs, outputting
  a CSV file of results.

  If you find any unusually-large diffs, these are likely the cause. These
  diffs should be deleted, and diff limits should be set.

* **One or more repositories are being slow to respond.**

  This is a problem with the repositories themselves, or a network issue
  in communicating with the repositories.

  To diagnose this, check your :file:`reviewboard.log` (see
  :ref:`logging-settings`) and look for any warnings or errors about file
  fetches taking too long.

* **The system is overloaded.**

  If you have your database, memcached, and web servers all on the same
  machine, you might be facing resource constraints.

  Check to make sure that you have enough memory available for processes,
  and run :command:`sudo dmesg` to see if any processes have been killed
  due to memory issues.

  You may need to re-evaluate your deployment and either upgrade your server
  or :ref:`scale out your deployment <scaling-deployment>`.


.. _CentOS Stream: https://www.centos.org/
.. _Debian: https://www.debian.org/
.. _Fedora: https://getfedora.org/
.. _Red Hat Enterprise: https://www.redhat.com/en
.. _Ubuntu: https://www.ubuntu.com/
.. _support: https://www.reviewboard.org/support/
