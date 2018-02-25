.. _installation-linux:

===================
Installing on Linux
===================


.. note::

   We recommend installing on a modern Ubuntu or Fedora distribution, as
   both are pretty well supported.

   You can run Review Board inside a Linux virtual machine running on top
   of `VMware ESXi`_ or `VMware Workstation Server`_.

   If you just want to get started with a simple install for evaluation
   purposes, we recommend installing `Review Board from Bitnami`_. They
   provide installers and virtual machines that you can start using
   immediately.

   Alternatively, we can host your Review Board server at RBCommons_.

.. _VMware ESXi:
   https://www.vmware.com/products/vsphere-hypervisor.html
.. _VMware Workstation Server:
   https://www.vmware.com/products/workstation-pro.html
.. _Review Board from Bitnami:
   https://bitnami.com/stack/reviewboard-plus-powerpack
.. _RBCommons: https://www.rbcommons.com/


Before You Begin
================

Review Board is provided as downloadable Python packages. The easy part is
installing Review Board itself. The harder part is installing some of the
dependencies, which we have less control over. This guide will help with some
of these dependencies.

It's assumed that you know which database and web server you want to use,
and have already installed these on your server. It's also assumed that
you have Python 2.7 installed.

Review Board supports the following database servers for production:

* MySQL_ (v5.6 or higher recommended)
* PostgreSQL_

And the following web servers:

* Apache_ + mod_wsgi

Other servers, such as nginx_ or lighttpd_, can be used as well, provided that
you have a standard WSGI loader. However, Review Board does not auto-generate
configurations for these servers.


The instructions below are assuming you're logged in as ``root`` or
are using :command:`sudo`.


.. _MySQL: https://www.mysql.com/
.. _PostgreSQL: https://www.postgresql.org/
.. _Apache: http://www.apache.org/
.. _nginx: https://www.nginx.com/
.. _lighttpd: http://www.lighttpd.net/


.. _linux-http-proxy:

Using a HTTP Proxy
------------------

If you're behind a proxy server, you'll need to set the :envvar:`http_proxy`
environment variable to your proxy server before running :command:`pip`. This
must be done as the user running :command:`pip`, in the same shell. For
example::

    $ sudo -s
    $ export http_proxy=http://proxy.example.com/
    $ pip install ....


If you're running CentOS, Red Hat, etc.
---------------------------------------

CentOS, RedHat, Scientific Linux, and other Enterprise Linux distributions
need to have the EPEL package repository added. Please see the
`instructions <http://fedoraproject.org/wiki/EPEL>`_ on adding the EPEL
package repositories to your system.

Once added, you can install Review Board and its dependencies by running::

    $ yum install ReviewBoard

You can then skip the rest of this guide for the required components. You may
still want to install optional components, such as
:ref:`Amazon S3 Support <linux-installing-amazon-s3-support>`.

You will still need to install your site. See :ref:`creating-sites` for
details.


Installing Pip and Setuptools
=============================

Before you begin, you'll need up-to-date versions of pip_ and
`Python setuptools`_.
Most Linux distributions have this available by default, but you can also
install them if needed thorugh your package repository.

See the `pip installation instructions`_ for details on how to install pip.

Once installed, make sure you have the very latest versions of pip and
setuptools available::

    $ pip install -U pip setuptools


.. _pip: https://pip.pypa.io/en/stable/
.. _Python setuptools: http://peak.telecommunity.com/DevCenter/setuptools
.. _pip installation instructions:
   https://pip.pypa.io/en/stable/installing/


Installing Required Dependencies
================================

You will need to install a handful of dependencies required by Review Board.
Some of these are required to install Review Board's dependencies, and some
are required at runtime.

To install on Debian_, Ubuntu_, or another Debian-based distribution, type::

    $ apt-get install build-essential python-dev libffi-dev libssl-dev patch


To install on a `RedHat Enterprise`_, Fedora_, CentOS_, or another
RedHat-based distribution, type::

    $ yum install gcc python-devel libffi-devel openssl-devel patch


.. index:: memcached

Installing Memcached
====================

Memcached
---------

Memcached_ is a high-performance caching server used by Review Board. While
optional, it's **strongly** recommended in order to have a fast, responsive
server. Along with memcached, we need the python-memcached Python bindings.

To install on Debian_ or Ubuntu_, type::

    $ apt-get install memcached

To install on `RedHat Enterprise`_, Fedora_ or CentOS_, type::

    $ yum install memcached

.. _memcached: https://memcached.org/


python-memcached
----------------

You'll need to install python-memcached. You can install this by typing::

    $ pip install python-memcached


Installing Review Board
=======================

To install Review Board and its required dependencies in one go, type::

    $ pip install ReviewBoard


This will automatically download and install the latest stable release of
Review Board and the required versions of its core dependencies.


Installing Database Bindings
============================

Depending on the database you plan to use, you will probably need additional
bindings.


MySQL
-----

To install, type::

    $ pip install -U mysql-python


Distributions may provide native packages. You may also need to install a mysql
development package first.

To install on Debian_ or Ubuntu_, type::

    $ apt-get install python-mysqldb


PostgreSQL
----------

To install, type::

    $ pip install -U psycopg2


Installing Source Control Components
====================================

Depending on which source control systems you plan to use, you will need
some additional components.


.. _installing-cvs:

CVS
---

To use Review Board with CVS_, you'll need the :command:`cvs` package
installed. This is available on almost every distribution.

To install on Debian_ or Ubuntu_, type::

    $ apt-get install cvs

To install on `RedHat Enterprise`_, Fedora_ or CentOS_, type::

    $ yum install cvs


.. _CVS: http://www.nongnu.org/cvs/


.. _installing-git:

Git
---

To install on Debian_ or Ubuntu_, type::

    $ apt-get install git-core

To install on Fedora_, type::

    $ yum install git-core

If your distribution doesn't provide Git_, you'll need to install it
manually from https://www.git-scm.com/.


.. _Git: https://www.git-scm.com/


Mercurial
---------

To install support for Mercurial_, type::

    $ pip install -U mercurial

You can also check your distribution for a native package, or use one of the
`binary packages <https://www.mercurial-scm.org/downloads>`_ provided.


.. _Mercurial: https://www.mercurial-scm.org/


Perforce
--------

To use Review Board with Perforce_, you'll first need to install
:command:`p4` some place in your web server's path (usually :file:`/usr/bin`).
You can download this from the `Perforce downloads`_ page.

You'll then need to install the Python bindings by typing the following::

    $ pip install p4python


.. _`Perforce downloads`: https://www.perforce.com/downloads
.. _Perforce: https://www.perforce.com/


.. _installing-svn:

Subversion
----------

To use Review Board with Subversion_, you'll need both subversion and
PySVN_ installed. In the event that PySVN cannot be installed, subvertpy_
may be used as an alternative, but we recommend PySVN for the best
compatibility.


.. _Subversion: http://subversion.tigris.org/
.. _PySVN: http://pysvn.tigris.org/
.. _subvertpy: https://www.samba.org/~jelmer/subvertpy/


PySVN
~~~~~

To install on Debian_ or Ubuntu_, type::

    $ apt-get install subversion python-svn

To install on Fedora_, type::

    $ yum install subversion pysvn

`RedHat Enterprise`_ and CentOS_ provide subversion, but you may have to
install PySVN from scratch if you do not wish to add the EPEL repository.
To install Subversion, type::

    $ yum install subversion

To install PySVN from EPEL, add its repository, then type::

    $ yum --enablerepo=epel install pysvn

If your distribution doesn't provide PySVN, you can install it by
`downloading <http://pysvn.tigris.org/project_downloads.html>`_ the latest
release and following the instructions in the provided :file:`INSTALL.html`.

subvertpy
~~~~~~~~~

.. note::

   subvertpy is only needed if you cannot install PySVN. We strongly
   recommend using PySVN for the best Subversion compatibility.

To install on Debian_ or Ubuntu_, type::

    $ apt-get install python-subvertpy

To install on Fedora_, type::

    $ yum install python-subvertpy

On `RedHat Enterprise`_ and CentOS_, you may have to install subvertpy from
scratch if you do not wish to add the EPEL repository. To install PySVN from
EPEL, add its repository, then type::

    $ yum --enablerepo=epel install python-subvertpy

If your distribution doesn't provide subvertpy, you can install it by
installing the development packages for Python and subversion, and then
the package itself via pip, by typing::

    $ pip install -U subvertpy


.. _linux-installing-amazon-s3-support:

Installing Amazon S3 Support (optional)
=======================================

This is an optional step.

Review Board can use `Amazon S3`_ to store uploaded screenshots. To install
this, you will need the :mod:`django-storages` module. Type::

    $ pip install -U django-storages

After you've installed Review Board and created your site, you will need
to configure this. See the :ref:`file-storage-settings` documentation for
more information.

.. _`Amazon S3`: https://aws.amazon.com/s3/


Installing OpenStack Swift Support (optional)
=============================================

This is an optional step.

Review Board can use `OpenStack Swift`_ to store uploaded screenshots. To
install this, you will need the :mod:`django-storage-swift` module. Type::

    $ pip install -U django-storage-swift

After you've installed Review Board and created your site, you will need
to configure this. See the :ref:`file-storage-settings` documentation for
more information.

.. _`OpenStack Swift`: https://docs.openstack.org/swift/latest/
.. _`Django-Evolution`: https://github.com/beanbaginc/django-evolution
.. _Django: https://www.djangoproject.com/
.. _flup: http://trac.saddi.com/flup
.. _paramiko: http://www.lag.net/paramiko/
.. _`Python Imaging Library`: http://www.pythonware.com/products/pil/


.. _Debian: https://www.debian.org/
.. _Ubuntu: https://www.ubuntu.com/
.. _`RedHat Enterprise`: https://www.redhat.com/en
.. _Fedora: https://getfedora.org/
.. _CentOS: https://www.centos.org/


After Installation
==================

Once you've finished getting Review Board itself installed, you'll want to
create your site. See :ref:`creating-sites` for details.
