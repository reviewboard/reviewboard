from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.translation import ugettext_lazy as _

from reviewboard.site.models import LocalSite


class Tool(models.Model):
    name = models.CharField(max_length=32, unique=True)
    class_name = models.CharField(max_length=128, unique=True)

    supports_authentication = property(
        lambda x: x.get_scmtool_class().supports_authentication)
    supports_raw_file_urls = property(
        lambda x: x.get_scmtool_class().supports_raw_file_urls)

    def __unicode__(self):
        return self.name

    def get_scmtool_class(self):
        path = self.class_name
        i = path.rfind('.')
        module, attr = path[:i], path[i+1:]

        try:
            mod = __import__(module, {}, {}, [attr])
        except ImportError, e:
            raise ImproperlyConfigured, \
                'Error importing SCM Tool %s: "%s"' % (module, e)

        try:
            return getattr(mod, attr)
        except AttributeError:
            raise ImproperlyConfigured, \
                'Module "%s" does not define a "%s" SCM Tool' % (module, attr)

    class Meta:
        ordering = ("name",)


class Repository(models.Model):
    name = models.CharField(max_length=64, unique=True)
    path = models.CharField(max_length=255, unique=True)
    mirror_path = models.CharField(max_length=255, blank=True)
    raw_file_url = models.CharField(max_length=255, blank=True)
    username = models.CharField(max_length=32, blank=True)
    password = models.CharField(max_length=128, blank=True)
    tool = models.ForeignKey(Tool, related_name="repositories")
    bug_tracker = models.CharField(max_length=256, blank=True)
    encoding = models.CharField(max_length=32, blank=True)
    visible = models.BooleanField(default=True)

    # Access control
    local_site = models.ForeignKey(LocalSite, blank=True, null=True)
    public = models.BooleanField(
        _('publicly accessible'),
        default=True,
        help_text=_('Review requests and files on public repositories are '
                    'visible to anyone. Private repositories must explicitly '
                    'list the users and groups that can access them.'))

    users = models.ManyToManyField(
        User,
        limit_choices_to={'is_active': True},
        blank=True,
        related_name='repositories',
        verbose_name=_('users'),
        help_text=_('A list of users with explicit access to the repository.'))
    review_groups = models.ManyToManyField(
        'reviews.Group',
        limit_choices_to={'invite_only': True},
        blank=True,
        related_name='repositories',
        verbose_name=_('review groups'),
        help_text=_('A list of invite-only review groups whose members have '
                    'explicit access to the repository.'))

    def get_scmtool(self):
        cls = self.tool.get_scmtool_class()
        return cls(self)

    def is_accessible_by(self, user):
        """Returns whether or not the user has access to the repository.

        The repository is accessibly by the user if it is public or
        the user has access to it (either by being explicitly on the allowed
        users list, or by being a member of a review group on that list).
        """
        return (self.public or
                (user.is_authenticated() and
                 (self.review_groups.filter(users__pk=user.pk).count() > 0 or
                  self.users.filter(pk=user.pk).count() > 0)))

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Repositories"
