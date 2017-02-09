.. _repository-scm-clearcase:

======================
ClearCase Repositories
======================

.. note::

   ClearCase support is community-driven. If you have improvements you want
   to see, or hit any problems, please discuss them on the
   `community support list`_.

Review Board supports posting and reviewing code on :rbintegration:`ClearCase
<clearcase>` repositories. Each ClearCase VOB needs its own repository in
Review Board.

To post changes for review, you will need to use RBTools_. This will generate
a diff suitable for posting to Review Board. See :ref:`Using RBTools with
ClearCase <rbt-post-clearcase>` for more information.


.. _community support list: https://groups.google.com/group/reviewboard
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing ClearCase Support
============================

Before you add the repository, you will need to make sure the
:command:`cleartool` command from ClearCase client is in your system path (or
in a place accessible by your web server's process).


Adding the Repository
=====================

To configure a ClearCase repository, first proceed to :ref:`add the repository
<adding-repositories>` and select :guilabel:`ClearCase` from the
:guilabel:`Repository type` field.

You will see a :guilabel:`Path` field, which should contain the VOB path for
your repository, representing either a `snapshot or dynamic view`_. The VOB
path must be an absolute path. On Windows, this must include the drive letter.
On Linux/UNIX, this must include the full mount point.


.. _snapshot or dynamic view:
   https://www-01.ibm.com/support/docview.wss?uid=swg21177694


Examples
--------

* ``/vobs/myrepo``
* ``C:\vobs\myrepo``
