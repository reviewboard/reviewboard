from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from reviewboard.reviews.managers import DefaultReviewerManager
from reviewboard.reviews.models.group import Group
from reviewboard.scmtools.models import Repository
from reviewboard.site.models import LocalSite


@python_2_unicode_compatible
class DefaultReviewer(models.Model):
    """Represents reviewers automatically added to review requests.

    A default reviewer entry automatically adds default reviewers to a
    review request when the diff modifies a file matching the ``file_regex``
    pattern specified.

    This is useful when different groups own different parts of a codebase.
    Adding DefaultReviewer entries ensures that the right people will always
    see the review request and discussions.

    A ``file_regex`` of ``".*"`` will add the specified reviewers by
    default for every review request.

    Note that this is keyed off the same LocalSite as its "repository" member.
    """
    name = models.CharField(_("name"), max_length=64)
    file_regex = models.CharField(
        _("file regex"),
        max_length=256,
        help_text=_("File paths are matched against this regular expression "
                    "to determine if these reviewers should be added."))
    repository = models.ManyToManyField(Repository, blank=True)
    groups = models.ManyToManyField(Group, verbose_name=_("default groups"),
                                    blank=True)
    people = models.ManyToManyField(User, verbose_name=_("default users"),
                                    related_name="default_review_paths",
                                    blank=True)
    local_site = models.ForeignKey(LocalSite, blank=True, null=True,
                                   related_name='default_reviewers')

    objects = DefaultReviewerManager()

    def is_accessible_by(self, user):
        """Returns whether the user can access this default reviewer."""
        if self.local_site and not self.local_site.is_accessible_by(user):
            return False

        return True

    def is_mutable_by(self, user):
        """Returns whether the user can modify or delete this default reviewer.

        Only those with the default_reviewer.change_group permission (such as
        administrators) can modify or delete default reviewers not bound
        to a LocalSite.

        LocalSite administrators can modify or delete them on their LocalSites.
        """
        return user.has_perm('reviews.change_default_reviewer',
                             self.local_site)

    def __str__(self):
        return self.name

    class Meta:
        app_label = 'reviews'
        verbose_name = _('default reviewer')
        verbose_name_plural = _('default reviewers')
