from __future__ import unicode_literals

import inspect
import logging
import uuid
import warnings
from time import time

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.db import IntegrityError
from django.utils import six, timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.http import urlquote
from django.utils.six.moves import range
from django.utils.translation import ugettext_lazy as _
from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.db.fields import JSONField
from djblets.log import log_timed

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import get_hosting_service
from reviewboard.scmtools.crypto_utils import (decrypt_password,
                                               encrypt_password)
from reviewboard.scmtools.managers import RepositoryManager, ToolManager
from reviewboard.scmtools.signals import (checked_file_exists,
                                          checking_file_exists,
                                          fetched_file, fetching_file)
from reviewboard.site.models import LocalSite


@python_2_unicode_compatible
class Tool(models.Model):
    name = models.CharField(max_length=32, unique=True)
    class_name = models.CharField(max_length=128, unique=True)

    objects = ToolManager()

    # Templates can't access variables on a class properly. It'll attempt to
    # instantiate the class, which will fail without the necessary parameters.
    # So, we use these as convenient wrappers to do what the template can't do.
    supports_raw_file_urls = property(
        lambda x: x.scmtool_class.supports_raw_file_urls)
    supports_ticket_auth = property(
        lambda x: x.scmtool_class.supports_ticket_auth)
    supports_pending_changesets = property(
        lambda x: x.scmtool_class.supports_pending_changesets)
    field_help_text = property(
        lambda x: x.scmtool_class.field_help_text)

    def __str__(self):
        return self.name

    def get_scmtool_class(self):
        if not hasattr(self, '_scmtool_class'):
            path = self.class_name
            i = path.rfind('.')
            module, attr = path[:i], path[i + 1:]

            try:
                mod = __import__(six.binary_type(module), {}, {},
                                 [six.binary_type(attr)])
            except ImportError as e:
                raise ImproperlyConfigured(
                    'Error importing SCM Tool %s: "%s"' % (module, e))

            try:
                self._scmtool_class = getattr(mod, attr)
            except AttributeError:
                raise ImproperlyConfigured(
                    'Module "%s" does not define a "%s" SCM Tool'
                    % (module, attr))

        return self._scmtool_class
    scmtool_class = property(get_scmtool_class)

    class Meta:
        ordering = ("name",)


@python_2_unicode_compatible
class Repository(models.Model):
    ENCRYPTED_PASSWORD_PREFIX = '\t'

    name = models.CharField(_('Name'), max_length=64)
    path = models.CharField(_('Path'), max_length=255)
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
    encrypted_password = models.CharField(max_length=128, blank=True,
                                          db_column='password')
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

    archived = models.BooleanField(
        _('Archived'),
        default=False,
        help_text=_("Archived repositories do not show up in lists of "
                    "repositories, and aren't open to new review requests."))

    archived_timestamp = models.DateTimeField(null=True, blank=True)

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

    hooks_uuid = models.CharField(
        _('Hooks UUID'),
        max_length=32,
        null=True,
        blank=True,
        help_text=_('Unique identifier used for validating incoming '
                    'webhooks.'))

    objects = RepositoryManager()

    BRANCHES_CACHE_PERIOD = 60 * 5  # 5 minutes
    COMMITS_CACHE_PERIOD_SHORT = 60 * 5  # 5 minutes
    COMMITS_CACHE_PERIOD_LONG = 60 * 60 * 24  # 1 day

    def _set_password(self, value):
        """Sets the password for the repository.

        The password will be stored as an encrypted value, prefixed with a
        tab character in order to differentiate between legacy plain-text
        passwords.
        """
        if value:
            value = '%s%s' % (self.ENCRYPTED_PASSWORD_PREFIX,
                              encrypt_password(value.encode('utf-8')))
        else:
            value = ''

        self.encrypted_password = value

    def _get_password(self):
        """Returns the password for the repository.

        If a password is stored and encrypted, it will be decrypted and
        returned.

        If the stored password is in plain-text, then it will be encrypted,
        stored in the database, and returned.
        """
        password = self.encrypted_password

        # NOTE: Due to a bug in 2.0.9, it was possible to get a string of
        #       "\tNone", indicating no password. We have to check for this.
        if not password or password == '\tNone':
            password = None
        elif password.startswith(self.ENCRYPTED_PASSWORD_PREFIX):
            password = password[len(self.ENCRYPTED_PASSWORD_PREFIX):]

            if password:
                password = decrypt_password(password).decode('utf-8')
            else:
                password = None
        else:
            # This is a plain-text password. Convert it.
            self.password = password
            self.save(update_fields=['encrypted_password'])

        return password

    password = property(_get_password, _set_password)

    def get_scmtool(self):
        cls = self.tool.get_scmtool_class()
        return cls(self)

    @cached_property
    def hosting_service(self):
        if self.hosting_account:
            return self.hosting_account.service

        return None

    @cached_property
    def bug_tracker_service(self):
        """Returns selected bug tracker service if one exists."""
        if self.extra_data.get('bug_tracker_use_hosting'):
            return self.hosting_service
        else:
            bug_tracker_type = self.extra_data.get('bug_tracker_type')
            if bug_tracker_type:
                bug_tracker_cls = get_hosting_service(bug_tracker_type)

                # TODO: we need to figure out some way of storing a second
                # hosting service account for bug trackers.
                return bug_tracker_cls(HostingServiceAccount())

        return None

    @property
    def supports_post_commit(self):
        """Whether or not this repository supports post-commit creation.

        If this is ``True``, the :py:meth:`get_branches` and
        :py:meth:`get_commits` methods will be implemented to fetch information
        about the committed revisions, and get_change will be implemented to
        fetch the actual diff. This is used by
        :py:meth:`ReviewRequestDraft.update_from_commit_id
        <reviewboard.reviews.models.ReviewRequestDraft.update_from_commit_id>`.
        """
        hosting_service = self.hosting_service

        if hosting_service:
            return hosting_service.supports_post_commit
        else:
            return self.get_scmtool().supports_post_commit

    def get_credentials(self):
        """Returns the credentials for this repository.

        This returns a dictionary with 'username' and 'password' keys.
        By default, these will be the values stored for the repository,
        but if a hosting service is used and the repository doesn't have
        values for one or both of these, the hosting service's credentials
        (if available) will be used instead.
        """
        username = self.username
        password = self.password

        if self.hosting_account and self.hosting_account.service:
            username = username or self.hosting_account.username
            password = password or self.hosting_account.service.get_password()

        return {
            'username': username,
            'password': password,
        }

    def get_or_create_hooks_uuid(self, max_attempts=20):
        """Returns a hooks UUID, creating one if necessary.

        If a hooks UUID isn't already saved, then this will try to generate one
        that doesn't conflict with any other registered hooks UUID. It will try
        up to `max_attempts` times, and if it fails, None will be returned.
        """
        if not self.hooks_uuid:
            for attempt in range(max_attempts):
                self.hooks_uuid = uuid.uuid4().hex

                try:
                    self.save(update_fields=['hooks_uuid'])
                    break
                except IntegrityError:
                    # We hit a collision with the token value. Try again.
                    self.hooks_uuid = None

            if not self.hooks_uuid:
                s = ('Unable to generate a unique hooks UUID for '
                     'repository %s after %d attempts'
                     % (self.pk, max_attempts))
                logging.error(s)
                raise Exception(s)

        return self.hooks_uuid

    def archive(self, save=True):
        """Archives a repository.

        The repository won't appear in any public lists of repositories,
        and won't be used when looking up repositories. Review requests
        can't be posted against an archived repository.

        New repositories can be created with the same information as the
        archived repository.
        """
        # This should be sufficiently unlikely to create duplicates. time()
        # will use up a max of 8 characters, so we slice the name down to
        # make the result fit in 64 characters
        self.name = 'ar:%s:%x' % (self.name[:50], int(time()))
        self.archived = True
        self.public = False
        self.archived_timestamp = timezone.now()

        if save:
            self.save()

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

    def get_branches(self):
        """Returns a list of branches."""
        hosting_service = self.hosting_service

        cache_key = make_cache_key('repository-branches:%s' % self.pk)
        if hosting_service:
            branches_callable = lambda: hosting_service.get_branches(self)
        else:
            branches_callable = self.get_scmtool().get_branches

        return cache_memoize(cache_key, branches_callable,
                             self.BRANCHES_CACHE_PERIOD)

    def get_commit_cache_key(self, commit):
        return 'repository-commit:%s:%s' % (self.pk, commit)

    def get_commits(self, branch=None, start=None):
        """Returns a list of commits.

        This is paginated via the 'start' parameter. Any exceptions are
        expected to be handled by the caller.
        """
        hosting_service = self.hosting_service

        commits_kwargs = {
            'branch': branch,
            'start': start,
        }

        if hosting_service:
            commits_callable = \
                lambda: hosting_service.get_commits(self, **commits_kwargs)
        else:
            commits_callable = \
                lambda: self.get_scmtool().get_commits(**commits_kwargs)

        # We cache both the entire list for 'start', as well as each individual
        # commit. This allows us to reduce API load when people are looking at
        # the "new review request" page more frequently than they're pushing
        # code, and will usually save 1 API request when they go to actually
        # create a new review request.
        if branch and start:
            cache_period = self.COMMITS_CACHE_PERIOD_LONG
        else:
            cache_period = self.COMMITS_CACHE_PERIOD_SHORT

        cache_key = make_cache_key('repository-commits:%s:%s:%s'
                                   % (self.pk, branch, start))
        commits = cache_memoize(cache_key, commits_callable,
                                cache_period)

        for commit in commits:
            cache.set(self.get_commit_cache_key(commit.id),
                      commit, self.COMMITS_CACHE_PERIOD_LONG)

        return commits

    def get_change(self, revision):
        """Get an individual change.

        This returns a tuple of (commit message, diff).
        """
        hosting_service = self.hosting_service

        if hosting_service:
            return hosting_service.get_change(self, revision)
        else:
            return self.get_scmtool().get_change(revision)

    def is_accessible_by(self, user):
        """Returns whether or not the user has access to the repository.

        The repository is accessibly by the user if it is public or
        the user has access to it (either by being explicitly on the allowed
        users list, or by being a member of a review group on that list).
        """
        if self.local_site and not self.local_site.is_accessible_by(user):
            return False

        return (self.public or
                user.is_superuser or
                (user.is_authenticated() and
                 (self.review_groups.filter(users__pk=user.pk).count() > 0 or
                  self.users.filter(pk=user.pk).count() > 0)))

    def is_mutable_by(self, user):
        """Returns whether or not the user can modify or delete the repository.

        The repository is mutable by the user if the user is an administrator
        with proper permissions or the repository is part of a LocalSite and
        the user has permissions to modify it.
        """
        return user.has_perm('scmtools.change_repository', self.local_site)

    def save(self, **kwargs):
        """Saves the repository.

        This will perform any data normalization needed, and then save the
        repository to the database.
        """
        # Prevent empty strings from saving in the admin UI, which could lead
        # to database-level validation errors.
        if self.hooks_uuid == '':
            self.hooks_uuid = None

        return super(Repository, self).save(**kwargs)

    def __str__(self):
        return self.name

    def _make_file_cache_key(self, path, revision, base_commit_id):
        """Makes a cache key for fetched files."""
        return 'file:%s:%s:%s:%s:%s' % (
            self.pk,
            urlquote(path),
            urlquote(revision),
            urlquote(base_commit_id or ''),
            urlquote(self.raw_file_url or ''))

    def _make_file_exists_cache_key(self, path, revision, base_commit_id):
        """Makes a cache key for file existence checks."""
        return 'file-exists:%s:%s:%s:%s:%s' % (
            self.pk,
            urlquote(path),
            urlquote(revision),
            urlquote(base_commit_id or ''),
            urlquote(self.raw_file_url or ''))

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
            tool = self.get_scmtool()
            argspec = inspect.getargspec(tool.get_file)

            if argspec.keywords is None:
                warnings.warn('SCMTool.get_file() must take keyword '
                              'arguments, signature for %s is deprecated.'
                              % tool.name, DeprecationWarning)
                data = tool.get_file(path, revision)
            else:
                data = tool.get_file(path, revision,
                                     base_commit_id=base_commit_id)

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

        This is called by get_file_exists if the file isn't already in the
        cache.

        This function is smart enough to check if the file exists in cache,
        and will use that for the result instead of making a separate call.
        """
        # First we check to see if we've fetched the file before. If so,
        # it's in there and we can just return that we have it.
        file_cache_key = make_cache_key(
            self._make_file_cache_key(path, revision, base_commit_id))

        if file_cache_key in cache:
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
                tool = self.get_scmtool()
                argspec = inspect.getargspec(tool.file_exists)

                if argspec.keywords is None:
                    warnings.warn('SCMTool.file_exists() must take keyword '
                                  'arguments, signature for %s is deprecated.'
                                  % tool.name, DeprecationWarning)
                    exists = tool.file_exists(path, revision)
                else:
                    exists = tool.file_exists(path, revision,
                                              base_commit_id=base_commit_id)

            checked_file_exists.send(sender=self,
                                     path=path,
                                     revision=revision,
                                     base_commit_id=base_commit_id,
                                     request=request,
                                     exists=exists)

        return exists

    def get_encoding_list(self):
        """Returns a list of candidate text encodings for files"""
        encodings = []
        for e in self.encoding.split(','):
            e = e.strip()
            if e:
                encodings.append(e)

        return encodings or ['iso-8859-15']

    def clean(self):
        """Clean method for checking null unique_together constraints.

        Django has a bug where unique_together constraints for foreign keys
        aren't checked properly if one of the relations is null. This means
        that users who aren't using local sites could create multiple groups
        with the same name.
        """
        super(Repository, self).clean()

        if self.local_site is None:
            q = Repository.objects.exclude(pk=self.pk)

            if q.filter(name=self.name).exists():
                raise ValidationError(
                    _('A repository with this name already exists'),
                    params={'field': 'name'})

            if q.filter(path=self.path).exists():
                raise ValidationError(
                    _('A repository with this path already exists'),
                    params={'field': 'path'})

    class Meta:
        verbose_name_plural = "Repositories"
        unique_together = (('name', 'local_site'),
                           ('archived_timestamp', 'path', 'local_site'),
                           ('hooks_uuid', 'local_site'))
