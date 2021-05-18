.. _upgrading-reviewboard:

======================
Upgrading Review Board
======================


Upgrading Review Board is pretty simple. It's essentially a three-step
process.

1. Upgrade Review Board by running:

   .. code-block:: shell

      $ pip install -U ReviewBoard

   If you previously installed using :command:`easy_install`, then you
   will instead need to do:

   .. code-block:: shell

      $ easy_install -U ReviewBoard

2. Upgrade each installed site. See :ref:`upgrading-sites`.
3. Restart your web server.
4. Restart memcached.

If you're on Linux and behind a proxy server, see the installation
instructions for :ref:`linux-http-proxy`.
