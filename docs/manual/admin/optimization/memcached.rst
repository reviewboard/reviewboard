.. _optimizing-memcached:

====================
Optimizing Memcached
====================

Memcached is a high-performance key/value caching server that operates
entirely in memory. We **strongly** recommend that you use it in order to
achieve the best performance. Review Board caches a lot of large pieces of
data, many of which are expensive to fetch or recompute, which is why a fast
caching layer is so important.

By default, memcached generally only sets aside a small amount of RAM for the
cache. This may differ depending on the operating system or Linux
distribution, but it varies between 64MB and 512MB.

The more memory you can give to memcached, the better. We recommend at least
2GB, if you can afford it. Large deployments may want to give even more.

To increase the amount of memory available to memcached, modify the value
passed along with ``-m``. This value is in megabytes. For example, to specify
2GB of cache space, pass ``-m 2048``.

Your setup most likely has a configuration file where you can set this. On
Linux, memcached stores its settings in :file:`/etc/memcached.conf`.
