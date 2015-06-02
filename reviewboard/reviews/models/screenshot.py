from __future__ import unicode_literals

import os

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from djblets.util.templatetags.djblets_images import thumbnail

from reviewboard.site.urlresolvers import local_site_reverse


@python_2_unicode_compatible
class Screenshot(models.Model):
    """A screenshot associated with a review request.

    Like diffs, a screenshot can have comments associated with it.
    These comments are of type
    :py:class:`reviewboard.reviews.models.ScreenshotComment`.
    """
    caption = models.CharField(_("caption"), max_length=256, blank=True)
    draft_caption = models.CharField(_("draft caption"),
                                     max_length=256, blank=True)
    image = models.ImageField(_("image"),
                              upload_to=os.path.join('uploaded', 'images',
                                                     '%Y', '%m', '%d'))

    @property
    def filename(self):
        """Returns the filename for display purposes."""
        return os.path.basename(self.image.name)

    def get_comments(self):
        """Returns all the comments made on this screenshot."""
        if not hasattr(self, '_comments'):
            self._comments = list(self.comments.all())

        return self._comments

    def get_thumbnail_url(self):
        """Returns the URL for the thumbnail, creating it if necessary."""
        return thumbnail(self.image)

    def thumb(self):
        """Creates and returns HTML for this screenshot's thumbnail."""
        url = self.get_thumbnail_url()
        return mark_safe('<img src="%s" data-at2x="%s" alt="%s" />' %
                         (url, thumbnail(self.image, '800x200'),
                          escape(self.caption)))
    thumb.allow_tags = True

    def __str__(self):
        return "%s (%s)" % (self.caption, self.image)

    def get_review_request(self):
        if hasattr(self, '_review_request'):
            return self._review_request

        try:
            return self.review_request.all()[0]
        except IndexError:
            try:
                return self.inactive_review_request.all()[0]
            except IndexError:
                # Maybe it's on a draft.
                try:
                    draft = self.drafts.get()
                except ObjectDoesNotExist:
                    draft = self.inactive_drafts.get()

                return draft.review_request

    def get_absolute_url(self):
        review_request = self.get_review_request()

        if review_request.local_site:
            local_site_name = review_request.local_site.name
        else:
            local_site_name = None

        return local_site_reverse(
            'screenshot',
            local_site_name=local_site_name,
            kwargs={
                'review_request_id': review_request.display_id,
                'screenshot_id': self.pk,
            })

    def save(self, **kwargs):
        super(Screenshot, self).save()

        try:
            draft = self.drafts.get()
            draft.timestamp = timezone.now()
            draft.save()
        except ObjectDoesNotExist:
            pass

    class Meta:
        app_label = 'reviews'
