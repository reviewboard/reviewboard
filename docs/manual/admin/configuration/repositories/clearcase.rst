.. _repository-scm-clearcase:

==================================
HCL VersionVault and IBM ClearCase
==================================

There are two editions of ClearCase support. The legacy :guilabel:`ClearCase`
edition is community-driven and has limited functionality and support. The
:guilabel:`VersionVault / ClearCase` edition is much more powerful and is
officially supported by the project and Beanbag, Inc.

For the VersionVault edition, it requires a license of `Power Pack`_. You can
`download a trial license`_ or `purchase a license`_ for your team.

To post changes for review, you will need to use RBTools_ 3.0 or newer. This
will generate a diff suitable for posting to Review Board. See :ref:`Using
RBTools with ClearCase and VersionVault <rbt-post-clearcase>` for more
information.


.. _Power Pack: https://www.reviewboard.org/powerpack/
.. _download a trial license: https://www.reviewboard.org/powerpack/trial/
.. _purchase a license: https://www.reviewboard.org/powerpack/purchase/
.. _RBTools: https://www.reviewboard.org/downloads/rbtools/


Installing ClearCase Support
============================

If you're using :guilabel:`VersionVault / ClearCase`, you'll need to install
and configure Power Pack. This also requires Review Board 4.0.5 or newer.

Before you add the repository, you will need to make sure the
:command:`cleartool` command from ClearCase client is in your system path (or
in a place accessible by your web server's process).


Adding the Repository (VersionVault / ClearCase)
================================================

To configure a VersionVault or ClearCase repository, first proceed to :ref:`add
the repository <adding-repositories>` and select :guilabel:`VersionVault /
ClearCase` from the :guilabel:`Repository type` field.

In the :guilabel:`Path` field, enter the absolute path to your view. This must
be either a `snapshot or dynamic view`_. On Windows, this must include the
drive letter.

For example::

    /view/rbview
    M:\vobs\rbview

For the :guilabel:`ClearCase VOBs` field, you'll need to enter the OID for each
VOB that you want included. To find the VOB OID, use this command (replacing
``<vobtag>`` with the tag of the VOB):

.. code-block:: console

    $ cleartool lsvob -l <vobtag> | grep "family uuid"

or on Windows:

.. code-block:: doscon

   # Command prompt
   C:\> cleartool lsvob -l <vobtag> | findstr /c:"family uuid"

   # PowerShell
   C:\> cleartool lsvob -l <vobtag> | Select-String "family uuid"

Copy the OIDs, and enter them in the field, one per line. For example::

    58a55679.ca1311eb.9c5d.52:54:00:7f:63:a5
    b25e48aa.d60511eb.838b.52:54:00:7f:63:a5
    2b2048ef.d60611eb.83af.52:54:00:7f:63:a5


.. _snapshot or dynamic view:
   https://www-01.ibm.com/support/docview.wss?uid=swg21177694


Adding the Repository (Legacy ClearCase)
========================================

The legacy ClearCase mode does not support VersionVault or UCM workflows. It
also can only support one VOB per repository. It is likely to be removed in the
future. If you need multiple VOBs or UCM support, you'll need to use the
VersionVault edition.

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
