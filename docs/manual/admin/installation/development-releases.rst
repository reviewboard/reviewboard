.. _installing-development-releases:

===============================
Installing Development Releases
===============================

When following the standard installation instructions, you will install the
latest stable release of Review Board, but if you prefer living on the edge or
helping out with testing, you can install in-development alpha/beta/RC
releases.

Note that if you install an in-development build, you may not be able to
downgrade back to a stable build due to changes to the database schema. Be
careful when running development builds on production servers, and always keep
back-ups of your database.


Installing In-Development Releases
==================================

In-development releases can be found in directories matching the format
:file:`{PackageName}/{majorVer}.{minorVer}` on the download server in the
`releases directory`_. For example, in-development builds for the 1.6 release
of the ReviewBoard package would live in
http://downloads.reviewboard.org/releases/ReviewBoard/1.6/.

To install a build from one of these directories, you can use the :option:`-f`
parameter to :command:`easy_install`. For example::

    $ easy_install -f http://downloads.reviewboard.org/releases/ReviewBoard/1.6/ -U ReviewBoard

If you want to install from this directory by default in future upgrades, you
can create a :file:`$HOME/.pydistutils.cfg` file and add the following::

    [easy_install]
    find_links = http://downloads.reviewboard.org/releases/ReviewBoard/1.6/

From then on, you can simply type::

    $ easy_install -U ReviewBoard

And any new versions found in that directory will be installed.


.. _`releases directory`: http://downloads.reviewboard.org/releases/
