.. _installation-linux:

===================
Installing on Linux
===================

Review Board is most commonly used on Linux, and supports the latest versions
of most major Linux distributions.

In this guide, we'll show you how to install Review Board yourself on Linux.
This will require a compatible version of Python, and several system packages.

If you're looking for a different solution, you may consider:

* :ref:`Deploying using Docker <installation-docker>`
* `Hosting with us on RBCommons <RBCommons_>`_

If you need any assistance, `reach out to us for support <support_>`_.


.. _RBCommons: https://rbcommons.com
.. _support: https://www.reviewboard.org/support/


Compatibility
=============


.. _supported-python:

Python
------

Review Board |version| supports Python |python_min_version| or higher.

If your Linux distribution does not come with a supported version of Python,
you may need to upgrade or look into a solution like :ref:`Docker
<installation-docker>`.

Alternatively, you can compile your own Python, along with mod_wsgi or
another server. This is only recommended if you're comfortable with this
process.


.. _supported-linux-distros:

Linux Distributions
-------------------

Review Board |version| is known to work with the following Linux
distributions:

* CentOS Stream 9
* Fedora 36
* Fedora 37
* Fedora 38
* Ubuntu 20.04 LTS
* Ubuntu 22.10 LTS

Other distributions may also work, as long as they provide a compatible
version of Python.

Review Board works on both X86 and ARM Linux distributions.


.. _supported-databases:

Databases
---------

..
    Update supported databases on release based on:

    https://code.djangoproject.com/wiki/SupportedDatabaseVersions


Review Board supports the following database servers for production:

* MySQL_ (v8 or higher recommended)
* PostgreSQL_ (v10 or higher recommended)

.. _MySQL: https://www.mysql.com/
.. _PostgreSQL: https://www.postgresql.org/


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


Preparing For Installation
==========================

Administrator Access
--------------------

This guide covers the following administrative actions:

* **Installing system packages.**

  This will use :command:`yum` for Red Hat-based distributions, and
  :command:`apt-get` for Debian-based distributions.

* **Creating system directories.**

  For example, :file:`/opt/reviewboard` for a Python Virtual Environment and
  :file:`/var/www/reviews.example.com` for a Review Board site directory.

This will typically require you to be a superuser (``root``).

We recommend switching to ``root`` before you begin the steps below:

.. code-block:: console

   $ sudo -s


.. _installation-python-virtualenv:

Python Virtual Environments vs. System Installs
-----------------------------------------------

A Python Virtual Environment is a self-contained copy of Python and a set of
packages. This is supported by Review Board, and comes with some advantages:

* **Isolation from system packages.**

  System upgrades won't break your Virtual Environment's packages, and
  Virtual Environment upgrades won't break your system.

* **Easier system migration and backups.**

  You can easily snapshot your entire environment and move or copy it between
  servers.

* **They're easy to set up and use.**

  These are not Virtual Machines or Docker images. They're just directories
  created on your system using a tool provided by your Linux distribution.

We recommend Virtual Environments for Review Board 5.0.5 and higher.

If you're working with an earlier install of Review Board, you have a **System
Install**.

Instructions are provided on each step for both Virtual Environments and
System Installs.

.. important::

   If you're using Ubuntu 23.04+, Fedora 38+, or another Linux distribution
   released after 2022, it may require you to use Virtual Environments.

   This is due to a Python standard called `PEP 668`_, which disables system
   installs of software like Review Board. If you see an error about
   "externally managed environments" when using :command:`pip`, this is the
   cause.

   If you're upgrading your Linux system to these releases, you will need to:

   1. Follow this guide to create a new Virtual Environment for Review Board.
   2. Either upgrade to Review Board 5.0.5+ or perform some manual changes to
      your web server to activate your Virtual Environment.

   `Contact support <support_>`_ for assistance in migrating your legacy
   install into a Virtual Environment.


.. _PEP 668: https://peps.python.org/pep-0668/


.. _linux-http-proxy:

Using a HTTP(S) Proxy
---------------------

If you're behind a proxy server, you'll need to set the :envvar:`http_proxy`
environment variable to your proxy server before running :command:`pip`. This
must be done as the user running :command:`pip`, in the same shell.

To enable a proxy:

.. code-block:: console

    $ export http_proxy=http://proxy.example.com/
    $ export https_proxy=https://proxy.example.com/


Let's Begin
===========

1. Install System Packages
--------------------------

You will need to install a handful of packages before installing Review Board:

.. tabs::

   .. code-tab:: console Debian/Ubuntu

      $ apt-get install build-essential python3-dev python3-pip \
                        libffi-dev libjpeg-dev libssl-dev patch \
                        libxml2-dev libxmlsec1-dev libxmlsec1-openssl \
                        python3-virtualenv

   .. code-tab:: console RHEL/Fedora/CentOS

      $ yum install gcc python3-devel libffi-devel openssl-devel patch perl \
                    libxml2-devel xmlsec1-devel xmlsec1-openssl-devel \
                    libtool-ltdl-devel python3-virtualenv


2. Create a Virtual Environment
-------------------------------

If you're installing using a :ref:`Python Virtual Environment
<installation-python-virtualenv>` instead of a System Install, you'll need
to create your environment:

.. code-block:: console

   $ virtualenv /opt/reviewboard

.. tip::

   This will use the default version of Python on your system.

   If you want to use a specific version of Python that you have installed,
   you can pass :option:`-p <pythonX.Y>`.

   For example:

   .. code-block:: console

      $ virtualenv -p python3.11 /opt/reviewboard

   This version **must** be supported by your web server!

.. important::

   Use :command:`virtualenv`, not :command:`python -m venv`.

   If you're familiar with Python already, you may be used to using
   :command:`python -m venv`, but this isn't suitable for Review Board. There
   are small differences in the virtual environment that will cause problems
   with activating the environment within the web server.


3. Install Review Board
-----------------------

To install Review Board and its required dependencies in one go:

.. tabs::

   .. code-tab:: console Python Virtual Environments

      $ /opt/reviewboard/bin/pip install ReviewBoard

   .. code-tab:: console System Installs

      $ pip3 install ReviewBoard


This will automatically download and install the latest stable release of
Review Board and the required versions of its core dependencies.

If you need to install a specific version:

.. tabs::

   .. code-tab:: console Python Virtual Environments

      $ /opt/reviewboard/pip install ReviewBoard==<version>

      # For example:
      $ /opt/reviewboard/pip install ReviewBoard==5.0.3

   .. code-tab:: console System Installs

      $ pip3 install ReviewBoard==<version>

      # For example:
      $ pip3 install ReviewBoard==5.0.3


4. Install Power Pack for Review Board (optional)
-------------------------------------------------

`Power Pack`_ is an optional licensed extension to Review Board. It adds
several additional features to Review Board that are useful to businesses and
enterprises, including:

* Report generation/analytics
* Document review
* Scalability enhancements
* Database import/export and conversion
* Support for additional source code management solutions:

  * :rbintegration:`Amazon CodeCommit <aws-codecommit>`
  * :rbintegration:`Bitbucket Server <bitbucket-server>`
  * :rbintegration:`Cliosoft SOS <cliosoft-sos>`
  * :rbintegration:`GitHub Enterprise <github-enterprise>`
  * :rbintegration:`HCL VersionVault <versionvault>`
  * :rbintegration:`IBM ClearCase <clearcase>`
  * :rbintegration:`Microsoft Azure DevOps / Team Foundation Server / TFS
    <tfs>`

60-day `Power Pack trial licenses`_ are available, and automatically convert
to a perpetual 2-user license after your trial period expires.

To install Power Pack:

.. tabs::

   .. code-tab:: console Python Virtual Environments

      $ /opt/reviewboard/bin/pip install -U ReviewBoardPowerPack

   .. code-tab:: console System Installs

      $ pip3 install -U ReviewBoardPowerPack


`Learn more about Power Pack <Power Pack_>`_.


.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _Power Pack trial licenses: https://www.reviewboard.org/powerpack/trial/


5. Install Database Support
---------------------------

Review Board can be used with MySQL, MariaDB, or Postgres databases. To use
these, you will need to install the appropriate packages.


.. _linux-mysql:

MySQL / MariaDB
~~~~~~~~~~~~~~~

1. Install system packages for MySQL/MariaDB:

   .. tabs::

      .. code-tab:: console Debian/Ubuntu

         $ apt-get install libmysqlclient-dev

      .. code-tab:: console RHEL/Fedora/CentOS

         $ yum install mariadb-connector-c-devel

         # Or:
         $ yum install mariadb-devel

2. Install the Python support in your environment.

   .. warning::

      You may have trouble installing some versions of mysqlclient_,
      depending on your Linux distribution.

      mysqlclient_ 2.2 supports MySQL 8.0.33+, but is incompatible with many
      Linux distributions (including Amazon Linux and Debian).

      We recommend trying to install the latest version. If that doesn't
      work, try installing 2.1.1. If you need help, `reach out to us for
      support <support_>`_.

      See the `mysqlclient documentation`_ and `bug tracker
      <mysqlclient-bug-tracker>`_ for more information.

   .. tabs::

      .. code-tab:: console Python Virtual Environments

         $ /opt/reviewboard/bin/pip install -U mysqlclient

         # To install 2.1.1:
         $ /opt/reviewboard/bin/pip install mysqlclient==2.1.1

      .. code-tab:: console System Installs

         $ pip3 install -U mysqlclient

         # To install 2.1.1:
         $ pip3 install mysqlclient==2.1.1


.. _mysqlclient: https://pypi.org/project/mysqlclient/
.. _mysqlclient documentation: https://github.com/PyMySQL/mysqlclient#install
.. _mysqlclient-bug-tracker:
   https://github.com/PyMySQL/mysqlclient/issues?q=is%3Aissue+


PostgreSQL
~~~~~~~~~~

.. tabs::

   .. code-tab:: console Python Virtual Environments

      $ /opt/reviewboard/bin/pip install -U 'ReviewBoard[postgres]'

   .. code-tab:: console System Installs

      $ pip3 install -U 'ReviewBoard[postgres]'


.. index:: memcached

6. Install Memcached
--------------------

Memcached_ is a high-performance caching server used by Review Board.

Review Board requires a memcached server, either locally or accessible over a
network.

.. tabs::

   .. code-tab:: console Debian/Ubuntu

      $ apt-get install memcached

   .. code-tab:: console RHEL/Fedora/CentOS

      $ yum install memcached

:ref:`Learn how to optimize memcached for Review Board
<optimizing-memcached>`.

.. tip::

   For better performance and scalability, install memcached on a separate
   server.

   You'll be asked to specify the memcached server address when you set up
   your Review Board site directory.


.. _memcached: https://memcached.org/


7. Install Repository Support (optional)
----------------------------------------

These are all optional, and depend on what kind of source code repositories
you need to work with.


.. _installing-cvs:

CVS
~~~

.. tabs::

   .. code-tab:: console Debian/Ubuntu

      $ apt-get install cvs

   .. code-tab:: console RHEL/Fedora/CentOS

      $ yum install cvs


.. _CVS: http://www.nongnu.org/cvs/


.. _installing-git:

Git
~~~

.. tabs::

   .. code-tab:: console Debian/Ubuntu

      $ apt-get install git

   .. code-tab:: console RHEL/Fedora/CentOS

      $ yum install git


.. _installing-mercurial:

Mercurial
~~~~~~~~~

.. code-block:: console

    $ pip3 install -U mercurial


.. _installing-perforce:

Perforce
~~~~~~~~

To use Review Board with Perforce_, you'll need to install both command
line tools and Python packages. These are both provided by Perforce.

1. Install the `Helix Command-Line Client`_ (:command:`p4`).

   .. tabs::

      .. group-tab:: Python Virtual Environments

         This must be placed in the web server's system path (for example,
         :file:`/opt/reviewboard/bin` or :file:`/usr/bin`).

      .. group-tab:: System Installs

         This must be placed in the web server's system path (for example,
         :file:`/usr/bin`).

2. Install Perforce's Python bindings:

   .. tabs::

      .. code-tab:: console Python Virtual Environments

         $ /opt/reviewboard/bin/pip install -U 'ReviewBoard[p4]'

      .. code-tab:: console System Installs

         $ pip3 install -U 'ReviewBoard[p4]'


.. _Helix Command-Line Client:
   https://www.perforce.com/downloads/helix-command-line-client-p4
.. _Perforce: https://www.perforce.com/


.. _installing-svn:

Subversion
~~~~~~~~~~

To use Review Board with Subversion_, you'll need both Subversion and
PySVN_ installed.

1. Install system packages for Subversion:

   .. tabs::

      .. code-tab:: console Debian/Ubuntu

         $ apt-get install subversion subversion-dev
         $ apt-get build-dep python3-svn

      .. code-tab:: console RHEL/Fedora/CentOS

         $ yum install subversion subversion-devel

2. Install PySVN:

   .. tabs::

      .. code-tab:: console Python Virtual Environments

         $ /opt/reviewboard/bin/pip install wheel
         $ curl https://pysvn.reviewboard.org | /opt/reviewboard/bin/python

      .. code-tab:: console System Installs

         $ pip3 install wheel
         $ curl https://pysvn.reviewboard.org | python3


Learn more about our `PySVN installer`_ if you need help. Simply follow the
instructions there.


.. note::

   Review Board previously supported an alternative to PySVN called
   Subvertpy. We've decided to drop Subvertpy support after many reports
   of compatibility issues.

   If you previously used Subvertpy, you will need to install PySVN instead.


.. _PySVN installer: https://github.com/reviewboard/pysvn-installer
.. _PySVN: docs/manual/admin/installation/linux.rst
.. _Subversion: https://subversion.apache.org/


8. Install Authentication Support (optional)
--------------------------------------------

Review Board can be connected to many kinds of authentication services,
including:

* Active Directory
* LDAP
* SAML Single Sign-On services
* NIS
* X.509 Public Keys

Some of these require installing additional support, which will be covered
here.

After you've installed Review Board and created your site, you will need to
configure your authentication method. See the :ref:`authentication-settings`
documentation for more information.

.. important::

   During setup, you will be asked to create an administrator user. This
   user will be set up as a "local user", so that it can always log into
   Review Board.

   Please choose a username that *not* already in your existing
   authentication service, to avoid any trouble logging in.


LDAP / Active Directory
~~~~~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. code-tab:: console Python Virtual Environments

      $ /opt/reviewboard/bin/pip install -U 'ReviewBoard[ldap]'

   .. code-tab:: console System Installs

      $ pip3 install -U 'ReviewBoard[ldap]'


SAML Single Sign-On
~~~~~~~~~~~~~~~~~~~

.. tabs::

   .. code-tab:: console Python Virtual Environments

      $ /opt/reviewboard/bin/pip install -U 'ReviewBoard[saml]'

   .. code-tab:: console System Installs

      $ pip3 install -U 'ReviewBoard[saml]'


9. Install CDN Support (optional)
---------------------------------

Review Board can optionally use various cloud services to store uploaded file
attachments, keeping them out of local storage.

After you've installed Review Board and created your site, you will need to
configure your cloud storage method. See the :ref:`file-storage-settings`
documentation for more information.


.. _linux-installing-amazon-s3-support:

Amazon S3
~~~~~~~~~

.. tabs::

   .. code-tab:: console Python Virtual Environments

      $ /opt/reviewboard/bin/pip install -U 'ReviewBoard[s3]'

   .. code-tab:: console System Installs

      $ pip3 install -U 'ReviewBoard[s3]'


`Learn more about Amazon S3 <https://aws.amazon.com/s3/>`_.


OpenStack Swift
~~~~~~~~~~~~~~~

.. tabs::

   .. code-tab:: console Python Virtual Environments

      $ /opt/reviewboard/bin/pip install -U 'ReviewBoard[swift]'

   .. code-tab:: console System Installs

      $ pip3 install -U 'ReviewBoard[swift]'


`Learn more about OpenStack Swift
<https://docs.openstack.org/swift/latest/>`_.


Installation is Complete! Next...
=================================

Congratulations on installing Review Board!

The next step is to create a :term:`site directory`. This directory will
contain your configuration, data files, file attachments, static media files
(CSS, JavaScript, and images), and more.

You can have multiple site directories on the same server, each serving a
separate Review Board install.

Let's create your first site directory. Continue on to :ref:`creating-sites`.


.. _CentOS Stream: https://www.centos.org/
.. _Debian: https://www.debian.org/
.. _Fedora: https://getfedora.org/
.. _Red Hat Enterprise: https://www.redhat.com/en
.. _Ubuntu: https://www.ubuntu.com/
