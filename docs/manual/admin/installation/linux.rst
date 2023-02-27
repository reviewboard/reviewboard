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

Currently, Review Board only auto-generates configurations for Apache +
mod_wsgi. Other configurations can be created based on that configuration.

.. _Apache: https://www.apache.org/
.. _gunicorn: https://gunicorn.org/
.. _nginx: https://www.nginx.com/
.. _uwsgi: https://uwsgi-docs.readthedocs.io/


Preparing For Installation
==========================

Administrator Access
--------------------

The instructions below assume you're running as a superuser (``root``) or
will be using :command:`sudo`.

If you're installing into a Python virtual environment, you won't need to use
:command:`sudo` for any :command:`pip` commands.


.. _linux-http-proxy:

Using a HTTP Proxy
------------------

If you're behind a proxy server, you'll need to set the :envvar:`http_proxy`
environment variable to your proxy server before running :command:`pip`. This
must be done as the user running :command:`pip`, in the same shell. For
example:

.. code-block:: console

    $ sudo -s
    $ export http_proxy=http://proxy.example.com/
    $ export https_proxy=https://proxy.example.com/
    $ pip3 install ....


Installing Required System Dependencies
=======================================

You will need to install a handful of dependencies required by Review Board.
Some of these are required to install Review Board's dependencies, and some
are required at runtime.

To install on Debian_ or Ubuntu_:

.. code-block:: console

    $ apt-get install build-essential python3-dev python3-pip
    $ apt-get install libffi-dev libjpeg-dev libssl-dev patch


To install on a `Red Hat Enterprise`_, Fedora_, or `CentOS Stream`_:

.. code-block:: console

    $ yum install gcc python3-devel libffi-devel openssl-devel patch perl


Installing Review Board
=======================

To install Review Board and its required dependencies in one go:

.. code-block:: console

    $ pip3 install ReviewBoard


This will automatically download and install the latest stable release of
Review Board and the required versions of its core dependencies.

If you need to install a specific version:

.. code-block:: console

   $ pip3 install ReviewBoard==<version>

   # For example:
   $ pip3 install ReviewBoard==5.0.3


Installing Power Pack for Review Board (optional)
=================================================

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

.. code-block:: console

    $ pip3 install -U ReviewBoardPowerPack


`Learn more about Power Pack <Power Pack_>`_.


.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _Power Pack trial licenses: https://www.reviewboard.org/powerpack/trial/


Installing Database Support
===========================

Review Board can be used with MySQL, MariaDB, or Postgres databases. To use
these, you will need to install the appropriate packages.


MySQL / MariaDB
---------------

To install on Debian_ or Ubuntu_:

.. code-block:: console

    $ apt-get install libmysqlclient-dev
    $ pip3 install -U 'ReviewBoard[mysql]'


To install on `Red Hat Enterprise`_, Fedora_ or `CentOS Stream`_:

.. code-block:: console

    $ yum install mariadb-connector-c-devel
    $ pip3 install -U 'ReviewBoard[mysql]'


PostgreSQL
----------

To install:

.. code-block:: console

    $ pip3 install -U 'ReviewBoard[postgres]'


.. index:: memcached

Installing Memcached
====================

Memcached_ is a high-performance caching server used by Review Board.

Review Board requires a memcached server, either locally or accessible over a
network.

To install memcached on Debian_ or Ubuntu_:

.. code-block:: console

    $ apt-get install memcached


To install memcached on `Red Hat Enterprise`_, Fedora_ or `CentOS Stream`_:

.. code-block:: console

    $ yum install memcached

:ref:`Learn how to optimize memcached for Review Board
<optimizing-memcached>`.


.. _memcached: https://memcached.org/


Installing Repository Support (optional)
========================================

These are all optional, and depend on what kind of source code repositories
you need to work with.


.. _installing-cvs:

CVS
---

To install on Debian_ or Ubuntu_:

.. code-block:: console

    $ apt-get install cvs

To install on `Red Hat Enterprise`_, Fedora_ or `CentOS Stream`_:

.. code-block:: console

    $ yum install cvs


.. _CVS: http://www.nongnu.org/cvs/


.. _installing-git:

Git
---

To install on Debian_ or Ubuntu_:

.. code-block:: console

    $ apt-get install git

To install on `Red Hat Enterprise`_, Fedora_ or `CentOS Stream`_:

.. code-block:: console

    $ yum install git


.. _installing-mercurial:

Mercurial
---------

To install:

.. code-block:: console

    $ pip3 install -U mercurial


.. _installing-perforce:

Perforce
--------

To use Review Board with Perforce_, you'll need to install both command
line tools and Python packages. These are both provided by Perforce.

1. Install the `Helix Command-Line Client`_ (:command:`p4`).

   This must be placed in the web server's system path (for example,
   :file:`/usr/bin`).

2. Install Perforce's Python bindings:

.. code-block:: console

    $ pip3 install -U 'ReviewBoard[p4]'


.. _Helix Command-Line Client:
   https://www.perforce.com/downloads/helix-command-line-client-p4
.. _Perforce: https://www.perforce.com/


.. _installing-svn:

Subversion
----------

To use Review Board with Subversion_, you'll need both Subversion and
PySVN_ installed.

To install on Debian_ or Ubuntu_:

.. code-block:: console

    $ apt-get install subversion python3-svn


To install on `Red Hat Enterprise`_, Fedora_ or `CentOS Stream`_:

.. code-block:: console

    $ yum install subversion subversion-devel
    $ pip3 install wheel
    $ curl https://pysvn.reviewboard.org | python3


Learn more about our `PySVN installer`_ if you need help. Simply follow the
instructions there.


.. note::

   Review Board previously supported an alternative to PySVN called
   Subvertpy. We've decided to drop Subvertpy support after many reports
   of compatibility issues.

   Subvertpy will continue to work through Review Board 5. However, we
   recommend uninstalling and upgrading to PySVN instead.


.. _PySVN installer: https://github.com/reviewboard/pysvn-installer
.. _PySVN: docs/manual/admin/installation/linux.rst
.. _Subversion: https://subversion.apache.org/


Installing Authentication Support (optional)
============================================

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
-----------------------

To install:

.. code-block:: console

    $ pip3 install -U 'ReviewBoard[ldap]'


SAML Single Sign-On
-------------------

To install:

.. code-block:: console

    $ pip3 install -U 'ReviewBoard[saml]'


Installing CDN Support (optional)
=================================

Review Board can optionally use various cloud services to store uploaded file
attachments, keeping them out of local storage.

After you've installed Review Board and created your site, you will need to
configure your cloud storage method. See the :ref:`file-storage-settings`
documentation for more information.


.. _linux-installing-amazon-s3-support:

Amazon S3
---------

To install:

.. code-block:: console

    $ pip3 install -U 'ReviewBoard[s3]'


`Learn more about Amazon S3 <https://aws.amazon.com/s3/>`_.


OpenStack Swift
---------------

To install:

.. code-block:: console

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
