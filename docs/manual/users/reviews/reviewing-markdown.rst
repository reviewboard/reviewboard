.. _reviewing-markdown:

========================
Reviewing Markdown Files
========================

Overview
========

When writing documentation using the :term:`Markdown` format, we often care
much less about the source file than the resulting rich text document.
Attaching a Markdown file (.md) to a review request will enable a special
review UI that will render the document.

To begin reviewing a Markdown file, click the thumbnail or the "Review" link
for the file attachment on the review request page.


Commenting on Blocks
====================

As you hover your mouse over parts of the document, top-level blocks will be
highlighted with a grey background. Clicking will pop open a new comment
dialog, just like in the diff viewer.

.. image:: comment-box.png

Comments support rich text using the :term:`Markdown` language. See
:ref:`using-markdown` for more information.

The file attachment comment dialog supports issue tracking. See the section on
:ref:`issue-tracking` for more information.

Once you're done writing your comment in the text area, click :guilabel:`Save`
to save the comment.

After saving a comment, a green comment flag will appear next to the block you
selected, indicating that you have an unpublished comment. If you want to edit
your comment, click the block or comment flag to pop open the comment box
again.


Reading Existing Comments
=========================

The Markdown review UI will show blue comment flags along the left-hand side of
the document. The number inside the comment flag indicates how many comments
were made on that block.

If you move the mouse cursor over the comment flag, a tooltip will appear
showing a summary of the comments made.

If you click on the block or the comment flag, the comment dialog will appear,
along with a blue side panel on the left showing those existing comments. You
can still write new comments in the green area of the comment box.

It's important to note that this is meant to be used as a reference to see if
other people have already said what you plan to say. The comment box is
**not** the place to reply to those comments. Instead, you can click the
:guilabel:`Reply` link next to the particular comment, which will take you
back to the review request page and open a reply box.


.. comment: vim: ft=rst et ts=3
