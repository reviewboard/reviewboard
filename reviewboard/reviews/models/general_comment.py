from __future__ import unicode_literals

from reviewboard.reviews.models.base_comment import BaseComment

from django.utils.translation import ugettext_lazy as _


class GeneralComment(BaseComment):
    """A comment on a review request that is not tied to any code or file.

    A general comment on a review request is used when a comment is not tied
    to specific lines of code or a special file attachment, and an issue is
    opened. Examples include suggestions for testing or pointing out errors
    in the change description.
    """
    anchor_prefix = 'gcomment'
    comment_type = 'general'

    def get_absolute_url(self):
        return self.get_review_url()

    class Meta:
        app_label = 'reviews'
        db_table = 'reviews_generalcomment'
        verbose_name = _('General Comment')
        verbose_name_plural = _('General Comments')
