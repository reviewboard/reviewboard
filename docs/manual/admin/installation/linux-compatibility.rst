.. _linux-compatibility:

==========================
Linux System Compatibility
==========================

Review Board requires a supported Linux or macOS system with Python 3.7 or
higher.

.. note::

   If you're using a non-default install of Python, you may need to use a web
   server such as gunicorn_, uwsgi_, or build an Apache ``mod_wsgi`` module
   for your server using mod_wsgi-express_.

.. _gunicorn: https://gunicorn.org/
.. _uwsgi: https://uwsgi-docs.readthedocs.io/en/latest/
.. _mod_wsgi-express: https://pypi.org/project/mod-wsgi/


Linux Compatibility
-------------------

The following Linux distributions are directly supported and tested:

* Amazon Linux 2023
* Arch Linux
* CentOS 9 Stream
* Debian 11 (Buster)
* Debian 12 (Bullseye)
* Debian 13 (Bookworm)
* Fedora 36
* Fedora 37
* Fedora 38
* Fedora 39
* Fedora 40
* openSUSE Tumbleweed
* Red Hat Enterprise Linux 9
* Rocky Linux 9
* Ubuntu 20.04
* Ubuntu 22.04
* Ubuntu 23.10


The following are known to work if you install a newer version of Python
(see :ref:`installation-installer-legacy-systems` below):

* :ref:`Amazon Linux 2 <installation-installer-amazon-linux-2>`
* :ref:`openSUSE Leap 15 <installation-installer-opensuse-leap-15>`
* :ref:`Red Hat Enterprise Linux 8 <installation-installer-rhel-8>`
* :ref:`Rocky Linux 8 <installation-installer-rockylinux-8>`
* :ref:`Ubuntu 18.04 <installation-installer-ubuntu-18-04>`


macOS Compatibility
-------------------

The following versions of macOS are directly supported and tested:

* macOS Ventura
* macOS Sonoma

Python 3 (provided by the macOS Command Line Developer Tools) and
Homebrew_ are currently required for installation on macOS.

.. _Homebrew: https://brew.sh


.. _installation-installer-legacy-systems:

Legacy Systems
--------------

We recommend installing Review Board on a modern, supported Linux
distribution.

Older systems may still work, but require additional steps, as shown below.

.. warning::

   You may not be able to install newer releases of Review Board on older
   systems, or use all Review Board features.

   This depends on the versions of Python or other dependencies available
   on the system.

   The installer will help you install the latest compatible version of
   Review Board.


.. _installation-installer-amazon-linux-2:

Amazon Linux 2
~~~~~~~~~~~~~~

Before installing on Amazon Linux 2, you will need to install a newer version
of Python:

.. code-block:: console

   $ sudo amazon-linux-extras install python3.8
   $ sudo yum install python38-devel

Then run the installer with :command:`python3.8`:

.. code-block:: console

   $ curl https://install.reviewboard.org | python3.8


.. _installation-installer-opensuse-leap-15:

openSUSE Leap 15
~~~~~~~~~~~~~~~~

Before installing on openSUSE Leap 15, you will need to install a newer
version of Python:

.. code-block:: console

   $ sudo zypper install python39 python39-devel

Then run the installation script with :command:`python3.9`:

.. code-block:: console

   $ curl https://install.reviewboard.org | python3.9


.. _installation-installer-rhel-8:

Red Hat Enterprise Linux 8
~~~~~~~~~~~~~~~~~~~~~~~~~~

Before installing on Red Hat Enterprise Linux 8, you will need to install a
newer version of Python:

.. code-block:: console

   $ sudo yum install -y python38 python38-devel

Then run the installation script with :command:`python3.8`:

.. code-block:: console

   $ curl https://install.reviewboard.org | python3.8

.. warning::

   Due to missing packages, Single Sign-On is not available on Red Hat
   Enterprise Linux 8.


.. _installation-installer-rockylinux-8:

Rocky Linux 8
~~~~~~~~~~~~~

Before installing on Rocky Linux 8, you will need to install a newer version
of Python:

.. code-block:: console

   $ sudo dnf module install python38
   $ sudo dnf install python38-devel

Then run the installation script with :command:`python3.8`:

.. code-block:: console

   $ curl https://install.reviewboard.org | python3.8

.. warning::

   Due to missing packages, Single Sign-On is not available on Rocky Linux 8.


.. _installation-installer-ubuntu-18-04:

Ubuntu 18.04
~~~~~~~~~~~~

Before installing on Ubuntu 18.04, you will need to install a newer version of
Python:

.. code-block:: console

   $ sudo apt-get install software-properties-common
   $ sudo add-apt-repository ppa:deadsnakes/ppa
   $ sudo apt-get install python3.8 python3.8-dev python3.8-venv

Then run the installation script with :command:`python3.8`:

.. code-block:: console

   $ curl https://install.reviewboard.org | python3.8

.. warning::

   Due to missing packages, Single Sign-On is not available on Ubuntu 18.04.


Installation is Complete! Next...
=================================

Congratulations on installing Review Board!

Continue on to :ref:`creating-sites`. If you've already created your site
directory through the installer, skip to :ref:`creating-sites-after-sitedir`.


.. _CentOS Stream: https://www.centos.org/
.. _Debian: https://www.debian.org/
.. _Fedora: https://getfedora.org/
.. _Red Hat Enterprise: https://www.redhat.com/en
.. _Ubuntu: https://www.ubuntu.com/
