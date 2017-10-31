====================
Reviews and Comments
====================

A review is a collection of comments and your indication of :ref:`approval
<approving-changes>` for a review request. All comments that you make
are grouped under a single draft review, which only you can see. When you've
finished your review, this draft can be :ref:`published <publishing-reviews>`,
allowing the owner of a review request and any other reviewers to see it and
discuss it.

Reviews consist of a header, a list of comments, and a footer. These are all
optional, and depend on the feedback you're giving. Most of your feedback will
be in the form of comments, which allow for :ref:`tracking issues
<issue-tracking>` that need to be fixed.

Reviews are created automatically when filing comments, or when clicking
:guilabel:`Review` in the review request action bar. You can manage them in the
:ref:`review draft banner <review-draft-banner>` or in the :ref:`review dialog
<review-dialog>`.


Ship It!
========

Reviews approving a change are represented with a "Ship It!" label. This means
that the person reviewing the change is happy with how things look and are
indicating their approval.

Changes can also be in a "Fix it, then Ship it!" state, which means that
they're happy once a couple of specific things are fixed.

See :ref:`approving-changes` for more information.


Review Headers
==============

A header is a block of free-form text displayed before any comments. It's
often used to provide a summary of your review, or to leave encouraging
feedback. Unlike comments, there is only one header allowed per review, and
they don't support :ref:`tracking issues <issue-tracking>` that need to be
fixed.

The header should not be used to review content. Instead, you'll want to file
comments instead.


Review Footers
==============

A footer is another block of free-form text, which is displayed after the
comments. It can be used to provide a conclusion of your review, which you
want people to read after they've gone through all your comments.


.. _general-comments:

General Comments
================

.. versionadded:: 3.0

General comments are a simple form of comment that applies to your review as a
whole, rather than to a diff or file attachment. There are many ways you might
use a general comment:

* Reporting a typo in the review request's description
* Requesting screenshots for UI changes
* Stating general problems with the change that aren't specific to certain
  code
* Recommending the review request owner seek reviews from a specific person or
  team

You can of course use this in any way you want, and you can have as many
general comments as you like. They also support :ref:`tracking issues
<issue-tracking>` that need to be fixed.

General comments are always shown before any other types of comments in the
review.


.. _file-attachment-comments:

File Attachment Comments
========================

Reviewers can :ref:`leave comments on file attachments
<reviewing-file-attachments>`.  Depending on the type of file attachment, this
might be on a line in a text file, an area of an image or PDF, or on the
entire file as a whole. For supported file types, reviews will show the
portion of the file being reviewed (such as a cropped part of the image
containing the comment).

File attachment comments are shown after general comments and before diff
comments, and support :ref:`tracking issues <issue-tracking>` that need to be
fixed.


.. _diff-comments:

Diff Comments
=============

Reviewers can also :ref:`leave comments on diffs <reviewing-diffs>` through
the Diff Viewer. These may be on a single line of code, or may span several
lines.

Reviews will show the lines of code that were commented on, along with the
nearest function or class preceding those lines. Hovering over this area will
also present controls for seeing more of the diff, helping to provide more
context to what you're seeing.

Diff comments are shown below any general comments and file attachments, and
of course support :ref:`tracking issues <issue-tracking>` that need to be
fixed.
