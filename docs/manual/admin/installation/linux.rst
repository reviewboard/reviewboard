.. _installation-linux:

===================
Installing on Linux
===================


.. note::

   We recommend installing on a modern Ubuntu or Fedora distribution, as
   both are pretty well supported.

   You can run Review Board inside a Linux virtual machine running on top
   of `VMware ESXi`_ or `VMware Workstation Server`_.

   Alternatively, we can host your Review Board server at RBCommons_.

.. _`VMware ESXi`:
   http://www.vmware.com/products/vsphere-hypervisor/overview.html
.. _`VMware Workstation Server`: http://www.vmware.com/products/workstation/overview.html
.. _RBCommons: http://www.rbcommons.com/


Before You Begin
================

Review Board is provided as downloadable packages through
`Python setuptools`_. The easy part is installing Review Board itself. The
harder part is installing some of the dependencies, which we have less control
over. This guide will help with some of these dependencies.

It's assumed that you know which database and web server you want to use,
and have already installed these on your server. It's also assumed that
you have Python v2.x (2.5 or newer) installed.

Review Board supports the following database servers:

* MySQL_ v5.0.31 or newer
* PostgreSQL_
* sqlite_ v3

And the following web servers:

* Apache_ + mod_wsgi, fastcgi, or mod_python
* lighttpd_ + fastcgi


The instructions below are assuming you're logged in as ``root`` or
are using :command:`sudo`.


.. _MySQL: http://www.mysql.com/
.. _PostgreSQL: http://www.postgresql.org/
.. _sqlite: http://www.sqlite.org/
.. _Apache: http://www.apache.org/
.. _lighttpd: http://www.lighttpd.net/


.. _linux-http-proxy:

Using a HTTP Proxy
------------------

If you're behind a proxy server, you'll need to set the :envvar:`http_proxy`
environment variable to your proxy server before running
:command:`easy_install`. This must be done as the user running
:command:`easy_install`, in the same shell. For example::

    $ sudo -s
    $ export http_proxy=http://proxy.example.com/
    $ easy_install ....


If you're running Fedora
------------------------

Fedora provides Review Board packages that are released shortly after we
perform new releases. To install Review Board and its dependencies on
Fedora, simply run::

    $ yum install ReviewBoard

You can then skip the rest of this guide for the required components. You may
still want to install optional components, such as
:ref:`Amazon S3 Support <linux-installing-amazon-s3-support>`.

You will still need to install your site. See :ref:`creating-sites` for
details.


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


Installing Python Setuptools
============================

Before you begin, you'll need `Python setuptools`_ version 0.6c9 or higher.
Most Linux distributions have this packaged and available for installation.

To install on Debian_, Ubuntu_, or another Debian-based distribution,
type::

    $ apt-get install python-setuptools


To install on Fedora_ 8 and above, type::

    $ yum install -y python-setuptools-devel.noarch

To install on a `RedHat Enterprise`_, CentOS_, Fedora_ 7 and earlier, or
another RedHat-based distribution, type::

    $ yum install python-setuptools


Users of other distributions should check with their distribution for native
packages, or follow the `setuptools installation`_ instructions.

If the version of setuptools available for your distribution is older than
0.6c9, you'll need to install it first, and then upgrade it to the latest
version by running::

    $ easy_install -U setuptools


.. _`Python setuptools`: http://peak.telecommunity.com/DevCenter/setuptools
.. _`setuptools installation`: http://peak.telecommunity.com/DevCenter/EasyInstall#installation-instructions


Installing Python Development Headers
=====================================

You will need to install the Python development headers for your
distribution.

To install on Debian_, Ubuntu_, or another Debian-based distribution,
type::

    $ apt-get install python-dev


To install on a `RedHat Enterprise`_, Fedora_, CentOS_, or another
RedHat-based distribution, type::

    $ yum install python-devel


.. index:: memcached

Installing memcached
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

.. _memcached: http://www.danga.com/memcached/


python-memcached
----------------

You'll need to install python-memcached. You can install this by typing::

    $ easy_install python-memcached


Installing patch
================

:command:`patch` is required for Review Board's diff viewer to work.
All distributions should provide this. We recommend using patch version 2.7 or
newer.

To install on Debian_ or Ubuntu_, type::

    $ apt-get install patch

To install on `RedHat Enterprise`_, Fedora_ or CentOS_, type::

    $ yum install patch


Installing Review Board
=======================

To install Review Board and its required dependencies (Djblets,
`Django-Evolution`_, Django_, flup_, paramiko_ and `Python Imaging Library`_)
in one go, type::

    $ easy_install ReviewBoard


This will automatically download and install the latest stable release of
Review Board and the required versions of its core dependencies.

If you want to install an in-development release, see
:ref:`installing-development-releases`.


Installing Database Bindings
============================

Depending on the database you plan to use, you will probably need additional
bindings.


MySQL
-----

To install, type::

    $ easy_install mysql-python


Distributions may provide native packages. You may also need to install a mysql
development package first.

To install on Debian_ or Ubuntu_, type::

    $ apt-get install python-mysqldb


PostgreSQL
----------

To install, type::

    $ easy_install psycopg2


Installing Source Control Components
====================================

Depending on which source control systems you plan to use, you will need
some additional components.


CVS
---

To use Review Board with CVS_, you'll need the :command:`cvs` package
installed. This is available on almost every distribution.

To install on Debian_ or Ubuntu_, type::

    $ apt-get install cvs

To install on `RedHat Enterprise`_, Fedora_ or CentOS_, type::

    $ yum install cvs


.. _CVS: http://www.nongnu.org/cvs/


Git
---

To install on Debian_ or Ubuntu_, type::

    $ apt-get install git-core

To install on Fedora_, type::

    $ yum install git-core

If your distribution doesn't provide Git_, you'll need to install it
manually from http://www.git-scm.com/.


.. _Git: http://www.git-scm.com/


Mercurial
---------

To install support for Mercurial_, type::

    $ easy_install mercurial

You can also check your distribution for a native package, or use one of the
`binary packages
<http://mercurial.selenic.com/wiki/Download>`_ provided.


.. _Mercurial: http://mercurial.selenic.com/


Perforce
--------

To use Review Board with Perforce_, you'll first need to install
:command:`p4` some place in your web server's path (usually :file:`/usr/bin`).
You can download this from the `Perforce downloads`_ page.

You'll then need to install the Python bindings by typing the following::

    $ easy_install P4PythonInstaller

This should fetch the appropriate versions of the ``p4api`` library and
compile it. This will require that you have standard build tools
(:command:`gcc`, :command:`make`, etc.) installed on your system.


.. _`Perforce downloads`: http://perforce.com/perforce/downloads/
.. _Perforce: http://www.perforce.com/


Subversion
----------

To use Review Board with Subversion_, you'll need both subversion and
either subvertpy_ installed. For backwards compatibility with older Review
Board installations, PySVN_ may be installed in place of subvertpy.


.. _Subversion: http://subversion.tigris.org/
.. _subvertpy: http://samba.org/~jelmer/subvertpy/
.. _PySVN: http://pysvn.tigris.org/

subvertpy
~~~~~~~~~

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
the package itself via easy_install, by typing::

    $ easy_install subvertpy

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


.. _linux-installing-amazon-s3-support:

Installing Amazon S3 Support (optional)
=======================================

This is an optional step.

Review Board can use `Amazon S3`_ to store uploaded screenshots. To install
this, you will need the :mod:`django-storages` module. Type::

    $ easy_install django-storages

After you've installed Review Board and created your site, you will need
to configure this. See the :ref:`file-storage-settings` documentation for
more information.

.. _`Amazon S3`: http://aws.amazon.com/s3/


Installing OpenStack Swift Support (optional)
=============================================

This is an optional step.

Review Board can use `OpenStack Swift`_ to store uploaded screenshots. To install
this, you will need the :mod:`django-storage-swift` module. Type::

    $ easy_install django-storage-swift

After you've installed Review Board and created your site, you will need
to configure this. See the :ref:`file-storage-settings` documentation for
more information.

.. _`OpenStack Swift`: http://swift.openstack.org/


Installing Development Tools (optional)
=======================================

If you plan to work on Review Board's source code, there are a few
additional packages you'll need to install:

* nose_
* Sphinx_

You can install these in one go by typing::

    $ easy_install nose Sphinx


.. _nose: http://somethingaboutorange.com/mrl/projects/nose/
.. _Sphinx: http://sphinx.pocoo.org/


.. _`Django-Evolution`: http://django-evolution.googlecode.com/
.. _Django: http://www.djangoproject.com/
.. _flup: http://trac.saddi.com/flup
.. _paramiko: http://www.lag.net/paramiko/
.. _`Python Imaging Library`: http://www.pythonware.com/products/pil/


.. _Debian: http://www.debian.org/
.. _Ubuntu: http://www.ubuntu.com/
.. _`RedHat Enterprise`: http://www.redhat.com/
.. _Fedora: http://fedoraproject.org/
.. _CentOS: http://www.centos.org/


After Installation
==================

Once you've finished getting Review Board itself installed, you'll want to
create your site. See :ref:`creating-sites` for details.
