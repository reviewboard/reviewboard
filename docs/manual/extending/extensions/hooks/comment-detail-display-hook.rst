.. _comment-detail-display-hook:

========================
CommentDetailDisplayHook
========================

:py:class:`reviewboard.extensions.hooks.CommentDetailDisplayHook` is used
when an extension wants to display additional information along with a comment
on a review or in an e-mail, such as from data posted using the API (perhaps
through an automated review), or from fields added to the comment dialog.

:py:class:`CommentDetailDisplayHook` has two functions that can be
implemented. Both are optional. These are passed the comment being rendered,
which may be a :py:class:`Comment` (for diff comments),
:py:class:`FileAttachmentComment`, :py:class:`ScreenshotComment`, or
:py:class:`GeneralComment`.

:py:meth:`render_review_comment_detail` renders comments for display in a
review on the review request page.

:py:meth:`render_email_comment_detail` renders comments for display in an
e-mail. It is passed an additional argument, ``is_html``, which will be
``True`` if rendering an HTML e-mail, or ``False`` if rendering a plain-text
e-mail. If rendering plain-text, the resulting string should always end
with a newline.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import CommentDetailDisplayHook


    class SampleCommentDetailDisplay(CommentDetailDisplayHook):
        def render_review_comment_detail(self, comment):
            return '<p>Severity: %s</p>' % comment.extra_data['severity']

        def render_email_comment_detail(self, comment, is_html):
            if is_html:
                return '<p>Severity: %s</p>' % comment.extra_data['severity']
            else:
                return 'Severity: %s\n' % comment.extra_data['severity']
