.. _installing-development-releases:

===============================
Installing Development Releases
===============================

When following the standard installation instructions, you will install the
latest stable release of Review Board, but if you prefer living on the edge or
helping out with testing, you can install in-development alpha/beta/RC
releases.

.. warning::

   If you install an in-development build, you may not be able to downgrade
   back to a stable build due to changes to the database schema.

   Be careful when running development builds on production servers, and
   always keep back-ups of your database.


Installing In-Development Releases
==================================

In-development releases can be found in directories matching the format
:file:`{PackageName}/{majorVer}.{minorVer}` on the download server in the
`releases directory`_.

To install a build from one of these directories, you'll need to tell
:command:`pip` to trust (:option:`--trusted-host`) our downloads server, to
find links (:option:`-f`) there, and to install pre-release builds
(:option:`-pre`). For example::

    $ pip --trusted-host downloads.reviewboard.org \
          -f https://downloads.reviewboard.org/releases/ReviewBoard/X.Y/ \
          --pre -U ReviewBoard

Replace ``X.Y`` with the desired version series. Any new pre-release versions
found there will be installed.


.. note::

   Often, pre-release builds will require pre-releases of other packages, such
   as ``rbintegrations``. Always check the release notes for the version you
   want to install for the most up-to-date instructions.


.. _releases directory: https://downloads.reviewboard.org/releases/
