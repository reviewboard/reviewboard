.. _contributing-patches:

====================
Contributing Patches
====================

New patches should always be based on our latest code in the ``master``
branch on the official `Git repository`_, unless your patch concerns a bug on
a particular release. In that case, it should be on the appropriate branch.
Release branches are in the form of :samp:`release-{major}.{minor}.x` (for
instance, `release-2.0.x` for the 2.0.x release series).

Patches should be posted on our project's Review Board server at
https://reviews.reviewboard.org/. We'll review the patches there, and
eventually submit the change if we agree it belongs in the codebase.

We do not accept patches to the `mailing lists`_, on our `bug tracker`_, or
through pull requests. If a patch is posted to these locations, we will ask
that it be resubmitted to our Review Board server.

Before submitting patches, please make sure the code adheres to the
:ref:`coding-standards`. You should also read our guides on
:ref:`keeping commits clean <clean-commit-histories>` and
:ref:`writing good change descriptions <writing-good-change-descriptions>`.

We also strongly encourage contributors to submit unit tests along with
their code.

.. _`Git repository`: https://github.com/reviewboard/reviewboard/
.. _`mailing lists`: https://www.reviewboard.org/mailing-lists/
.. _`bug tracker`: https://www.reviewboard.org/bugs/
