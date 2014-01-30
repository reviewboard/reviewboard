======================
Upgrading Review Board
======================


Upgrading Review Board is pretty simple. It's essentially a three-step
(optionally four-step) process.

1. Upgrade Review Board by running::

   $ easy_install -U ReviewBoard

2. Upgrade each installed site. See :ref:`upgrading-sites`.
3. Restart your web server.
4. Restart memcached, if installed.

If you're on Linux and behind a proxy server, see the installation
instructions for :ref:`linux-http-proxy`.
