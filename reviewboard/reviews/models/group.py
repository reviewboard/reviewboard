from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from djblets.db.fields import CounterField, JSONField

from reviewboard.reviews.managers import ReviewGroupManager
from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse


def _initialize_incoming_request_count(group):
    from reviewboard.reviews.models.review_request import ReviewRequest

    return ReviewRequest.objects.to_group(
        group,
        local_site=group.local_site).count()


@python_2_unicode_compatible
class Group(models.Model):
    """A group of people who can be targetted for review.

    This is usually used to separate teams at a company or components of a
    project.

    Each group can have an e-mail address associated with it, sending
    all review requests and replies to that address. If that e-mail address is
    blank, e-mails are sent individually to each member of that group.
    """
    name = models.SlugField(_("name"), max_length=64, blank=False)
    display_name = models.CharField(_("display name"), max_length=64)
    mailing_list = models.CharField(
        _("mailing list"),
        blank=True,
        max_length=254,
        help_text=_("The mailing list review requests and discussions "
                    "are sent to."))
    users = models.ManyToManyField(User, blank=True,
                                   related_name="review_groups",
                                   verbose_name=_("users"))
    local_site = models.ForeignKey(LocalSite, blank=True, null=True)

    incoming_request_count = CounterField(
        _('incoming review request count'),
        initializer=_initialize_incoming_request_count)

    invite_only = models.BooleanField(
        _('invite only'),
        default=False,
        help_text=_('If checked, only the users listed below will be able '
                    'to view review requests sent to this group.'))
    visible = models.BooleanField(default=True)

    extra_data = JSONField(null=True)

    objects = ReviewGroupManager()

    def is_accessible_by(self, user, request=None, silent=False):
        """Returns true if the user can access this group."""
        if self.local_site and not self.local_site.is_accessible_by(user):
            if not silent:
                logging.warning('Group pk=%d (%s) is not accessible by user '
                                '%s because its local_site is not accessible '
                                'by that user.',
                                self.pk, self.name, user, request=request)
            return False

        if not self.invite_only or user.is_superuser:
            return True

        if user.is_authenticated() and self.users.filter(pk=user.pk).exists():
            return True

        if not silent:
            logging.warning('Group pk=%d (%s) is not accessible by user %s '
                            'because it is invite only, and the user is not a '
                            'member.',
                            self.pk, self.name, user, request=request)

        return False

    def is_mutable_by(self, user):
        """Returns whether or not the user can modify or delete the group.

        The group is mutable by the user if they are  an administrator with
        proper permissions, or the group is part of a LocalSite and the user is
        in the admin list.
        """
        return user.has_perm('reviews.change_group', self.local_site)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        if self.local_site_id:
            local_site_name = self.local_site.name
        else:
            local_site_name = None

        return local_site_reverse('group', local_site_name=local_site_name,
                                  kwargs={'name': self.name})

    def clean(self):
        """Clean method for checking null unique_together constraints.

        Django has a bug where unique_together constraints for foreign keys
        aren't checked properly if one of the relations is null. This means
        that users who aren't using local sites could create multiple groups
        with the same name.
        """
        super(Group, self).clean()

        if (self.local_site is None and
            Group.objects.filter(name=self.name).exclude(pk=self.pk).exists()):
            raise ValidationError(
                _('A group with this name already exists'),
                params={'field': 'name'})

    class Meta:
        app_label = 'reviews'
        unique_together = (('name', 'local_site'),)
        verbose_name = _('review group')
        verbose_name_plural = _('review groups')
        ordering = ['name']
