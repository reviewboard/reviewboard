.. program:: rbinstall

.. _installation-installer:

=======================
Installing Review Board
=======================

The Review Board Installer can help you get going with Review Board in
minutes.

It's :ref:`compatible with a wide range
<installation-installer-requirements-systems>` of Linux distributions and
macOS versions, and takes care of installing all system and Review Board
packages and guiding you through creating your Site Directory.

.. tip::

   A :term:`Site Directory` will contain your Review Board configuration, data
   files, uploaded file attachments, static media files (CSS, JavaScript, and
   images), and more.

   You can have multiple Site Directories on the same server, each serving a
   separate internal Review Board website. These will all share the same
   Review Board install.

   You'll create your first Site Directory once Review Board is installed.

If you're looking for a different solution, you may consider:

* :ref:`Deploying using Docker <installation-docker>`
* `Hosting with us on RBCommons <RBCommons_>`_ (the official Review Board
  SaaS)

If you need any assistance, `reach out to us for support <support_>`_.


.. _RBCommons: https://rbcommons.com
.. _support: https://www.reviewboard.org/support/


.. _installation-installer-requirements:

System Requirements
===================

.. tip::

   Want to skip this and begin installation? Jump to
   :ref:`installation-installer-running`.


.. _supported-linux-distros:
.. _installation-installer-requirements-systems:

Compatible Systems
------------------

Review Board supports the following systems:

* Amazon Linux
* Apple macOS
* Arch Linux
* CentOS
* Debian
* Fedora
* openSUSE
* Red Hat Enterprise Linux
* Rocky Linux
* Ubuntu
* WSL2 for Windows

Review Board works on both X86 and ARM systems.

For a full list of compatible Linux versions, see :ref:`linux-compatibility`.


.. _supported-python:
.. _installation-installer-requirements-python:

Python
------

The Review Board installer requires Python 3.7 or higher.

Review Board itself follows the `Python end-of-life`_ release schedule. The
installer will show you the latest available version of Review Board
compatible with your system.

If your Linux distribution does not come with a compatible version of Python,
you may need to upgrade your distribution or look into a solution like
:ref:`Docker <installation-docker>` or RBCommons_.


.. _Python end-of-life: https://endoflife.date/python


.. _supported-databases:
.. _installation-installer-requirements-databases:

Databases
---------

..
    Update supported databases on release based on:

    https://code.djangoproject.com/wiki/SupportedDatabaseVersions


Review Board supports the following database servers for production:

* MySQL_ (v8 or higher)
* PostgreSQL_ (v12 or higher)

.. _MySQL: https://www.mysql.com/
.. _PostgreSQL: https://www.postgresql.org/


.. _installation-installer-requirements-webservers:

Web Servers
-----------

Review Board is known to work with the following web servers:

* Apache_ + mod_wsgi
* gunicorn_
* nginx_
* uwsgi_

Sample configurations are generated automatically for these servers.

.. _Apache: https://www.apache.org/
.. _gunicorn: https://gunicorn.org/
.. _nginx: https://www.nginx.com/
.. _uwsgi: https://uwsgi-docs.readthedocs.io/


.. _installation-installer-running:

Running the Installer
=====================

It's time to install Review Board!

Follow the simple steps below to begin, or learn about the
:ref:`advanced options <installation-installer-advanced>` for unattended
installs or configuring HTTP(S) proxies.

1. **Make sure you're a superuser.**

   The installer will need to install system packages. You will need to
   make sure you are running as ``root``:

   .. code-block:: console

      $ sudo -s

2. **Run the installer.**

   .. code-block:: console

      $ curl https://install.reviewboard.org | python3

   Alternatively, you can run the installer using pipx_ (if installed):

   .. code-block:: console

      $ pipx run rbinstall

   .. tip::

      You can install Review Board for a specific version of Python. For
      example:

      .. code-block:: console

         $ curl https://install.reviewboard.org | python3.11

         # or:

         $ pipx run --python python3.11 rbinstall

3. **Follow the installation steps.**

   The installer will guide you through the following steps:

   1. Checking your system for compatibility
   2. Choosing an install location
   3. Showing the commands that will be run
   4. Performing the installation
   5. Guiding you through :ref:`creating your Site Directory
      <creating-sites>` or importing an existing Site Directory.

   Instructions are provided all throughout, helping you make informed choices
   about your installation.

   You can cancel the installation at any point by pressing :kbd:`Control-C`.


.. _pipx: https://github.com/pypa/pipx


.. _installation-installer-advanced:

Advanced Options
================

.. _installation-installer-unattended:

Unattended Installs
-------------------

Review Board can be installed in Unattended Mode. This avoids prompting for
input, and is used for automated deployments to servers in your
infrastructure.

To begin an unattended install, specify ``--noinput``:

.. code-block:: console

   # Note the single "-" before the arguments.
   $ curl https://install.reviewboard.org | python3 - --noinput

   # or:

   $ pipx run rbinstall --noinput

By default, this will install to :file:`/opt/reviewboard`. You can customize
this by passign ``--install-path=<PATH>``. For example:

.. code-block:: console

   $ curl https://install.reviewboard.org | python3 - --noinput \
       --install-path=/usr/local/reviewboard

   # or:

   $ pipx run rbinstall --noinput --install-path=/usr/local/reviewboard

Run with ``--help`` to see additional options for specifying the Review Board
version or controlling other aspects of the install.


.. _linux-http-proxy:

Using a HTTP(S) Proxy
---------------------

If you're behind a proxy server, you'll need to set the :envvar:`http_proxy`
environment variable before you run the installer.

To enable a proxy:

.. code-block:: console

    $ export http_proxy=http://proxy.example.com/
    $ export https_proxy=https://proxy.example.com/


Installation is Complete! Next...
=================================

Congratulations on installing Review Board!

Continue on to :ref:`creating-sites`. If you've already created your site
directory through the installer, skip to :ref:`creating-sites-after-sitedir`.
