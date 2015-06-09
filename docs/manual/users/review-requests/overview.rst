.. _review-requests-overview:

========
Overview
========

All work in Review Board is centered around a :term:`review request`. Each
review request represents a coherent work item that's undergoing the code
review or editing process, be it a prospective code change, design document, or
other piece of work.

A review request is split into several sections and views. When you first open
a review request, you'll see a large box at the top which contains all of the
information about the request.

.. image:: review-request-details.png

At the top-right are the two major views for the review request: The first is
the :guilabel:`Reviews` view, which has all of the reviews that people have
done, as well as a record of the changes that have been made to the review
request. The second is the :guilabel:`Diff` view, which shows the code changes
themselves.

Next to the view tabs are several action commands, both for manipulating the
state of the review request, as well as performing reviews. At the top-left are
visibility controls (:ref:`star-archive-and-mute`).

.. TODO: link to docs on archive/mute once they're written

The review request box itself is primarily devoted to user-supplied information
about whatever is under review. There are several fields such as a one-line
summary and long-form description, as well as pieces of metadata such as the
branch that the code change has been made on, links to any relevant bugs, and a
list of people and groups who are being asked to review this review request.
See :ref:`review-request-fields` for more information.

Below the fields are any file attachments that have been added to the review
request. Like the diff, file attachments can each be individually reviewed. See
:ref:`uploading-files` and :ref:`reviewing-file-attachments` for more details.

At the bottom of the review request box is a table which lists all of the open
issues for this review request. :ref:`Issues <issue-tracking>` are created when
people add a comment and mark it as an issue, and are a convenient way of
keeping track of the work left to do.


Drafts
======

When a review request is first created, it is marked as a :term:`draft`, and is
not yet visible to anyone other than the author. This is shown by the presence
of a green :term:`draft bar` at the top of the page. Once everything has been
set up to the author's liking, clicking :guilabel:`Publish` will publish the
review request to all of the chosen reviewers.

When any changes are made to a published review request, including uploading a
new revision of the diff or making changes to any of the fields, a new draft
will be created. The changes will not be visible to anyone until that draft is
published.
