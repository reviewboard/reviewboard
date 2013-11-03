from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _
from djblets.log import log_timed
from djblets.util.fields import JSONField
from djblets.util.misc import cache_memoize, make_cache_key

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.scmtools.managers import RepositoryManager, ToolManager
from reviewboard.scmtools.signals import checked_file_exists, \
                                         checking_file_exists, \
                                         fetched_file, fetching_file
from reviewboard.site.models import LocalSite


class Tool(models.Model):
    name = models.CharField(max_length=32, unique=True)
    class_name = models.CharField(max_length=128, unique=True)

    objects = ToolManager()

    # Templates can't access variables on a class properly. It'll attempt to
    # instantiate the class, which will fail without the necessary parameters.
    # So, we use these as convenient wrappers to do what the template can't do.
    supports_authentication = property(
        lambda x: x.scmtool_class.supports_authentication)
    supports_raw_file_urls = property(
        lambda x: x.scmtool_class.supports_raw_file_urls)
    supports_ticket_auth = property(
        lambda x: x.scmtool_class.supports_ticket_auth)
    field_help_text = property(
        lambda x: x.scmtool_class.field_help_text)

    def __unicode__(self):
        return self.name

    def get_scmtool_class(self):
        if not hasattr(self, '_scmtool_class'):
            path = self.class_name
            i = path.rfind('.')
            module, attr = path[:i], path[i+1:]

            try:
                mod = __import__(module, {}, {}, [attr])
            except ImportError, e:
                raise ImproperlyConfigured, \
                    'Error importing SCM Tool %s: "%s"' % (module, e)

            try:
                self._scmtool_class = getattr(mod, attr)
            except AttributeError:
                raise ImproperlyConfigured, \
                    'Module "%s" does not define a "%s" SCM Tool' \
                    % (module, attr)

        return self._scmtool_class
    scmtool_class = property(get_scmtool_class)

    class Meta:
        ordering = ("name",)


class Repository(models.Model):
    name = models.CharField(max_length=64)
    path = models.CharField(max_length=255)
    mirror_path = models.CharField(max_length=255, blank=True)
    raw_file_url = models.CharField(
        _('Raw file URL mask'),
        max_length=255,
        blank=True,
        help_text=_("A URL mask used to check out a particular revision of a "
                    "file using HTTP. This is needed for repository types "
                    "that can't access remote files natively. "
                    "Use <tt>&lt;revision&gt;</tt> and "
                    "<tt>&lt;filename&gt;</tt> in the URL in place of the "
                    "revision and filename parts of the path."))
    username = models.CharField(max_length=32, blank=True)
    password = models.CharField(max_length=128, blank=True)
    extra_data = JSONField(null=True)

    tool = models.ForeignKey(Tool, related_name="repositories")
    hosting_account = models.ForeignKey(
        HostingServiceAccount,
        related_name='repositories',
        verbose_name=_('Hosting service account'),
        blank=True,
        null=True)

    bug_tracker = models.CharField(
        _('Bug tracker URL'),
        max_length=256,
        blank=True,
        help_text=_("This should be the full path to a bug in the bug tracker "
                    "for this repository, using '%s' in place of the bug ID."))
    encoding = models.CharField(
        max_length=32,
        blank=True,
        help_text=_("The encoding used for files in this repository. This is "
                    "an advanced setting and should only be used if you're "
                    "sure you need it."))
    visible = models.BooleanField(
        _('Show this repository'),
        default=True,
        help_text=_('Use this to control whether or not a repository is '
                    'shown when creating new review requests. Existing '
                    'review requests are unaffected.'))

    # Access control
    local_site = models.ForeignKey(LocalSite,
                                   verbose_name=_('Local site'),
                                   blank=True,
                                   null=True)
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
        verbose_name=_('Users with access'),
        help_text=_('A list of users with explicit access to the repository.'))
    review_groups = models.ManyToManyField(
        'reviews.Group',
        limit_choices_to={'invite_only': True},
        blank=True,
        related_name='repositories',
        verbose_name=_('Review groups with access'),
        help_text=_('A list of invite-only review groups whose members have '
                    'explicit access to the repository.'))

    objects = RepositoryManager()

    def get_scmtool(self):
        cls = self.tool.get_scmtool_class()
        return cls(self)

    @property
    def hosting_service(self):
        if self.hosting_account:
            return self.hosting_account.service

        return None

    def get_file(self, path, revision, base_commit_id=None, request=None):
        """Returns a file from the repository.

        This will attempt to retrieve the file from the repository. If the
        repository is backed by a hosting service, it will go through that.
        Otherwise, it will attempt to directly access the repository.
        """
        # We wrap the result of get_file in a list and then return the first
        # element after getting the result from the cache. This prevents the
        # cache backend from converting to unicode, since we're no longer
        # passing in a string and the cache backend doesn't recursively look
        # through the list in order to convert the elements inside.
        #
        # Basically, this fixes the massive regressions introduced by the
        # Django unicode changes.
        return cache_memoize(
            self._make_file_cache_key(path, revision, base_commit_id),
            lambda: [self._get_file_uncached(path, revision, base_commit_id,
                                             request)],
            large_data=True)[0]

    def get_file_exists(self, path, revision, base_commit_id=None,
                        request=None):
        """Returns whether or not a file exists in the repository.

        If the repository is backed by a hosting service, this will go
        through that. Otherwise, it will attempt to directly access the
        repository.

        The result of this call will be cached, making future lookups
        of this path and revision on this repository faster.
        """
        key = self._make_file_exists_cache_key(path, revision, base_commit_id)

        if cache.get(make_cache_key(key)) == '1':
            return True

        exists = self._get_file_exists_uncached(path, revision,
                                                base_commit_id, request)

        if exists:
            cache_memoize(key, lambda: '1')

        return exists

    def is_accessible_by(self, user):
        """Returns whether or not the user has access to the repository.

        The repository is accessibly by the user if it is public or
        the user has access to it (either by being explicitly on the allowed
        users list, or by being a member of a review group on that list).
        """
        if self.local_site and not self.local_site.is_accessible_by(user):
            return False

        return (self.public or
                (user.is_authenticated() and
                 (self.review_groups.filter(users__pk=user.pk).count() > 0 or
                  self.users.filter(pk=user.pk).count() > 0)))

    def is_mutable_by(self, user):
        """Returns whether or not the user can modify or delete the repository.

        The repository is mutable by the user if the user is an administrator
        with proper permissions or the repository is part of a LocalSite and
        the user is in the admin list.
        """
        return (user.has_perm('scmtools.change_repository') or
                (self.local_site and self.local_site.is_mutable_by(user)))

    def __unicode__(self):
        return self.name

    def _make_file_cache_key(self, path, revision, base_commit_id):
        """Makes a cache key for fetched files."""
        return "file:%s:%s:%s:%s" % (self.pk, urlquote(path),
                                     urlquote(revision),
                                     urlquote(base_commit_id or ''))

    def _make_file_exists_cache_key(self, path, revision, base_commit_id):
        """Makes a cache key for file existence checks."""
        return "file-exists:%s:%s:%s:%s" % (self.pk, urlquote(path),
                                            urlquote(revision),
                                            urlquote(base_commit_id or ''))

    def _get_file_uncached(self, path, revision, base_commit_id, request):
        """Internal function for fetching an uncached file.

        This is called by get_file if the file isn't already in the cache.
        """
        fetching_file.send(sender=self,
                           path=path,
                           revision=revision,
                           base_commit_id=base_commit_id,
                           request=request)

        if base_commit_id:
            timer_msg = "Fetching file '%s' r%s (base commit ID %s) from %s" \
                        % (path, revision, base_commit_id, self)
        else:
            timer_msg = "Fetching file '%s' r%s from %s" \
                        % (path, revision, self)

        log_timer = log_timed(timer_msg, request=request)

        hosting_service = self.hosting_service

        if hosting_service:
            data = hosting_service.get_file(
                self,
                path,
                revision,
                base_commit_id=base_commit_id)
        else:
            data = self.get_scmtool().get_file(path, revision)

        log_timer.done()

        fetched_file.send(sender=self,
                          path=path,
                          revision=revision,
                          base_commit_id=base_commit_id,
                          request=request,
                          data=data)

        return data

    def _get_file_exists_uncached(self, path, revision, base_commit_id,
                                  request):
        """Internal function for checking that a file exists.

        This is called by get_file_eixsts if the file isn't already in the
        cache.

        This function is smart enough to check if the file exists in cache,
        and will use that for the result instead of making a separate call.
        """
        # First we check to see if we've fetched the file before. If so,
        # it's in there and we can just return that we have it.
        file_cache_key = make_cache_key(
            self._make_file_cache_key(path, revision, base_commit_id))

        if cache.has_key(file_cache_key):
            exists = True
        else:
            # We didn't have that in the cache, so check from the repository.
            checking_file_exists.send(sender=self,
                                      path=path,
                                      revision=revision,
                                      base_commit_id=base_commit_id,
                                      request=request)

            hosting_service = self.hosting_service

            if hosting_service:
                exists = hosting_service.get_file_exists(
                    self,
                    path,
                    revision,
                    base_commit_id=base_commit_id)
            else:
                exists = self.get_scmtool().file_exists(path, revision)

            checked_file_exists.send(sender=self,
                                     path=path,
                                     revision=revision,
                                     base_commit_id=base_commit_id,
                                     request=request,
                                     exists=exists)

        return exists

    class Meta:
        verbose_name_plural = "Repositories"
        # TODO: the path:local_site unique constraint causes problems when
        # archiving repositories. We should really remove this constraint from
        # the tables and enforce it in code whenever visible=True
        unique_together = (('name', 'local_site'),
                           ('path', 'local_site'))
