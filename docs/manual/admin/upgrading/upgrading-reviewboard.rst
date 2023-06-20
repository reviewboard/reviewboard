.. _upgrading-reviewboard:

======================
Upgrading Review Board
======================

Upgrading Review Board is simple. It's essentially a three-step process.

1. Upgrade Review Board by running:

   .. tabs::

      .. code-tab:: console Python Virtual Environments

         $ /opt/reviewboard/bin/pip install -U ReviewBoard

      .. code-tab:: console System Installs

         $ pip3 install -U ReviewBoard

   This may need to be done as ``root``, or using :command:`sudo`, depending
   on your setup.

2. :ref:`Upgrade your site directory <upgrading-sites>`.
3. Restart your web server.

If you're on Linux and behind a proxy server, see the installation
instructions for :ref:`linux-http-proxy`.
