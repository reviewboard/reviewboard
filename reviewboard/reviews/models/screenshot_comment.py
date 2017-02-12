from __future__ import unicode_literals

from django.db import models
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from djblets.util.templatetags.djblets_images import crop_image

from reviewboard.reviews.models.base_comment import BaseComment
from reviewboard.reviews.models.screenshot import Screenshot


class ScreenshotComment(BaseComment):
    """A comment on a screenshot."""
    anchor_prefix = "scomment"
    comment_type = "screenshot"
    screenshot = models.ForeignKey(Screenshot, verbose_name=_('screenshot'),
                                   related_name="comments")

    # This is a sub-region of the screenshot.  Null X indicates the entire
    # image.
    x = models.PositiveSmallIntegerField(_("sub-image X"), null=True)
    y = models.PositiveSmallIntegerField(_("sub-image Y"))
    w = models.PositiveSmallIntegerField(_("sub-image width"))
    h = models.PositiveSmallIntegerField(_("sub-image height"))

    def get_image_url(self):
        """Returns the URL for the thumbnail, creating it if necessary."""
        return crop_image(self.screenshot.image, self.x, self.y,
                          self.w, self.h)

    def image(self):
        """Returns HTML for a section of the screenshot for this comment.

        This will generate the cropped part of the screenshot referenced by
        this comment and returns the HTML markup embedding it.
        """
        return '<img src="%s" width="%s" height="%s" alt="%s" />' % \
            (self.get_image_url(), self.w, self.h, escape(self.text))

    class Meta(BaseComment.Meta):
        verbose_name = _('screenshot comment')
        verbose_name_plural = _('screenshot comments')
