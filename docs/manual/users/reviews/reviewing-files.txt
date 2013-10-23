.. _reviewing-file-attachments:

==========================
Reviewing File Attachments
==========================

.. versionadded:: 1.6

File attachments can be reviewed using Review Board. Some file types, such as
images, have special interfaces for doing reviews.

To learn how to review image files, read ref:`Reviewing Images <reviewing-images>`.

For other files, reviewers can download the files, and add comments to the
attachment as a whole.

.. image:: ../review-requests/file-attachment.png

The file attachment box provides a :guilabel:`Add Comment` button. Clicking
this button pops up a comment dialog that works exactly like the dialog you
get when :doc:`reviewing diffs <reviewing-diffs>`.

.. image:: comment-box.png

Comments support rich text using the :term:`Markdown` language. See
:ref:`using-markdown` for more information.

The file attachment comment dialog supports issue tracking. See the section on
:ref:`issue-tracking` for more information.

As of Review Board 1.6.0, there's no visual indication of an existing comment
on the file attachment. However, you can see your comment and edit it by
clicking :guilabel:`Add Comment` again.


.. comment: vim: ft=rst et ts=3
