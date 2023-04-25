======================
Review Board Workflows
======================

There are many ways you can use Review Board, depending on the code review
strategy, source code management system, and internal policies.

This page covers the general workflows for :ref:`pre-commit review
<pre-commit-review>` and :ref:`post-commit review <post-commit-review>`.

We also have detailed guides for using Review Board with specific source code
management systems:

* :ref:`Cliosoft SOS <rbtools-workflow-sos>`
* :ref:`Git <rbtools-workflow-git>`
* :ref:`IBM ClearCase / HCL VersionVault <rbtools-workflow-versionvault>`
* :ref:`Perforce <rbtools-workflow-perforce>`


.. _using-pre-commit-review:

Using Pre-Commit Review
=======================

Review Board supports many different workflows, but most people use a
:term:`pre-commit review` model. This is considered a Best Practice for
code review.

Review Board is built to fully support the pre-commit review process:

1. Make a change to your local source tree.

2. :ref:`Create a review request <creating-review-requests>` for your new
   change.

   This can be done through the web or, more commonly, through the :ref:`rbt
   post <rbtools:rbt-post>` command line tool (which integrates with all
   supported repositories).

3. :ref:`Publish the review request <publishing-review-requests>` and wait for
   your reviewers to see it on their :ref:`Dashboard <dashboard>`.

4. Wait for feedback from the reviewers.

   Reviewers can discuss the change, :ref:`open issues <issue-tracking>`, or
   :ref:`approve the change <approving-changes>`.

5. If reviewers have :ref:`opened issues <issue-tracking>` to request changes:

   1. Update the code in your tree.

   2. Update the review request with your new change, and describe those
      changes in the update.

   3. :ref:`Publish the review request <publishing-review-requests>`.

   4. GOTO 4.

6. If reviewers :ref:`approve the  change ("Ship It!") <approving-changes>`:

   1. Push your change to the upstream repository.

   2. Click :menuselection:`Close --> Completed` on the review request
      action bar.

      This may happen automatically, if the repository is configured to
      auto-close review requests.

..
    :term:`post-commit review` and internal workflows may be different. If you've
    joined a company that uses Review Board, and you're unsure about your specific
    process, you'll want to talk to your employer to find out the specifics.


.. _using-post-commit-review:

Using Post-Commit Review
========================

Post-commit review is less common in modern development, but is still a
supported workflow in Review Board:

1. Make changes to your source tree and push them upstream.

2. :ref:`Create a review request <creating-review-requests>` for your new
   change.

   You can browse through the list of commits within Review Board and then
   post it for review, or use the :ref:`rbt post <rbtools:rbt-post>` command
   line tool to post instead.

3. :ref:`Publish the review request <publishing-review-requests>` and wait for
   your reviewers to see it on their :ref:`Dashboard <dashboard>`.

   Reviewers can discuss the change, :ref:`open issues <issue-tracking>`, or
   :ref:`approve the change <approving-changes>`.

4. Wait for feedback from the reviewers.

5. If reviewers have :ref:`opened issues <issue-tracking>` to request changes:

   1. Create new commits with the fixes and push them upstream.

   2. Update the review request with your new change, and describe those
      changes in the update.

      You will need to update this with a new commit by either
      :ref:`uploading a new diff <uploading-diffs>` or using :ref:`rbt post
      <rbtools:rbt-post>`.

   3. :ref:`Publish the review request <publishing-review-requests>`.

   4. GOTO 4.

6. If reviewers :ref:`approve the  change ("Ship It!") <approving-changes>`:

   1. Click :menuselection:`Close --> Completed` on the review request
      action bar.

      This may happen automatically, if the repository is configured to
      auto-close review requests.


Note that some features in Review Board (such as :term:`interdiffs`) are built
with a pre-commit review workflow in mind.
