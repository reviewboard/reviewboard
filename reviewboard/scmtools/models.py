from __future__ import unicode_literals

import logging
import uuid
import warnings
from importlib import import_module
from time import time

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError, models
from django.db.models import Q
from django.utils import six, timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.http import urlquote
from django.utils.six.moves import range
from django.utils.translation import ugettext_lazy as _
from djblets.cache.backend import cache_memoize, make_cache_key
from djblets.db.fields import JSONField
from djblets.log import log_timed
from djblets.util.decorators import cached_property

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
    """A configured source code management tool.

    Each :py:class:`~reviewboard.scmtools.core.SCMTool` used by repositories
    must have a corresponding :py:class:`Tool` entry. These provide information
    on the capabilities of the tool, and accessors to construct a tool for
    a repository.

    Tool entries are populated by running the ``registerscmtools`` management
    command.
    """

    name = models.CharField(max_length=32, unique=True)
    class_name = models.CharField(max_length=128, unique=True)

    objects = ToolManager()

    # Templates can't access variables on a class properly. It'll attempt to
    # instantiate the class, which will fail without the necessary parameters.
    # So, we use these as convenient wrappers to do what the template can't do.

    #: Whether or not the SCMTool supports review requests with history.
    #:
    #: See :py:attr:`SCMTool.supports_history
    #: <reviewboard.scmtools.core.SCMTool.supports_history>` for details.
    supports_history = property(
        lambda x: x.scmtool_class.supports_history)

    #: Whether custom URL masks can be defined to fetching file contents.
    #:
    #: See :py:attr:`SCMTool.supports_raw_file_urls
    #: <reviewboard.scmtools.core.SCMTool.supports_raw_file_urls>` for details.
    supports_raw_file_urls = property(
        lambda x: x.scmtool_class.supports_raw_file_urls)

    #: Whether ticket-based authentication is supported.
    #:
    #: See :py:attr:`SCMTool.supports_ticket_auth
    #: <reviewboard.scmtools.core.SCMTool.supports_ticket_auth>` for details.
    supports_ticket_auth = property(
        lambda x: x.scmtool_class.supports_ticket_auth)

    #: Whether server-side pending changesets are supported.
    #:
    #: See :py:attr:`SCMTool.supports_pending_changesets
    #: <reviewboard.scmtools.core.SCMTool.supports_pending_changesets>` for
    #: details.
    supports_pending_changesets = property(
        lambda x: x.scmtool_class.supports_pending_changesets)

    #: Overridden help text for the configuration form fields.
    #:
    #: See :py:attr:`SCMTool.field_help_text
    #: <reviewboard.scmtools.core.SCMTool.field_help_text>` for details.
    field_help_text = property(
        lambda x: x.scmtool_class.field_help_text)

    @property
    def scmtool_id(self):
        """The unique ID for the SCMTool.

        Type:
            unicode
        """
        return self.scmtool_class.scmtool_id

    def get_scmtool_class(self):
        """Return the configured SCMTool class.

        Returns:
            type:
            The subclass of :py:class:`~reviewboard.scmtools.core.SCMTool`
            backed by this Tool entry.

        Raises:
            django.core.exceptions.ImproperlyConfigured:
                The SCMTool could not be found.
        """
        if not hasattr(self, '_scmtool_class'):
            path = self.class_name
            i = path.rfind('.')
            module, attr = path[:i], path[i + 1:]

            try:
                mod = import_module(module)
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

    def __str__(self):
        """Return the name of the tool.

        Returns:
            unicode:
            The name of the tool.
        """
        return self.name

    class Meta:
        db_table = 'scmtools_tool'
        ordering = ('name',)
        verbose_name = _('Tool')
        verbose_name_plural = _('Tools')


@python_2_unicode_compatible
class Repository(models.Model):
    """A configured external source code repository.

    Each configured Repository entry represents a source code repository that
    Review Board can communicate with as part of the diff uploading and
    viewing process.

    Repositories are backed by a
    :py:class:`~reviewboard.scmtools.core.SCMTool`, which functions as a client
    for the type of repository and can fetch files, load lists of commits and
    branches, and more.

    Access control is managed by a combination of the :py:attr:`public`,
    :py:attr:`users`, and :py:attr:`groups` fields. :py:attr:`public` controls
    whether a repository is publicly-accessible by all users on the server.
    When ``False``, only users explicitly listed in :py:attr:`users` or users
    who are members of the groups listed in :py:attr:`groups` will be able
    to access the repository or view review requests posted against it.
    """

    #: The amount of time branches are cached, in seconds.
    #:
    #: Branches are cached for 5 minutes.
    BRANCHES_CACHE_PERIOD = 60 * 5

    #: The short period of time to cache commit information, in seconds.
    #:
    #: Some commit information (such as retrieving the latest commits in a
    #: repository) should result in information cached only for a short
    #: period of time. This is set to cache for 5 minutes.
    COMMITS_CACHE_PERIOD_SHORT = 60 * 5

    #: The long period of time to cache commit information, in seconds.
    #:
    #: Commit information that is unlikely to change should be kept around
    #: for a longer period of time. This is set to cache for 1 day.
    COMMITS_CACHE_PERIOD_LONG = 60 * 60 * 24  # 1 day

    #: The fallback encoding for text-based files in repositories.
    #:
    #: This is used if the file isn't valid UTF-8, and if the repository
    #: doesn't specify a list of encodings.
    FALLBACK_ENCODING = 'iso-8859-15'

    #: The error message used to indicate that a repository name conflicts.
    NAME_CONFLICT_ERROR = _('A repository with this name already exists')

    #: The error message used to indicate that a repository path conflicts.
    PATH_CONFLICT_ERROR = _('A repository with this path already exists')

    #: The prefix used to indicate an encrypted password.
    #:
    #: This is used to indicate whether a stored password is in encrypted
    #: form or plain text form.
    ENCRYPTED_PASSWORD_PREFIX = '\t'

    name = models.CharField(_('Name'), max_length=255)
    path = models.CharField(_('Path'), max_length=255)
    mirror_path = models.CharField(max_length=255, blank=True)
    raw_file_url = models.CharField(
        _('Raw file URL mask'),
        max_length=255,
        blank=True)
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

    @property
    def password(self):
        """The password for the repository.

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
                password = decrypt_password(password)
            else:
                password = None
        else:
            # This is a plain-text password. Convert it.
            self.password = password
            self.save(update_fields=['encrypted_password'])

        return password

    @password.setter
    def password(self, value):
        """Set the password for the repository.

        The password will be stored as an encrypted value, prefixed with a
        tab character in order to differentiate between legacy plain-text
        passwords.
        """
        if value:
            value = '%s%s' % (self.ENCRYPTED_PASSWORD_PREFIX,
                              encrypt_password(value))
        else:
            value = ''

        self.encrypted_password = value

    @property
    def scmtool_class(self):
        """The SCMTool subclass used for this repository.

        Type:
            type:
            A subclass of :py:class:`~reviewboard.scmtools.core.SCMTool`.
        """
        if self.tool_id is not None:
            return self.tool.get_scmtool_class()

        return None

    @cached_property
    def hosting_service(self):
        """The hosting service providing this repository.

        This will be ``None`` if this is a standalone repository.

        Type:
            reviewboard.hostingsvcs.service.HostingService
        """
        if self.hosting_account:
            return self.hosting_account.service

        return None

    @cached_property
    def bug_tracker_service(self):
        """The selected bug tracker service for the repository.

        This will be ``None`` if this repository is not associated with a bug
        tracker.

        Type:
            reviewboard.hostingsvcs.service.HostingService
        """
        if self.extra_data.get('bug_tracker_use_hosting'):
            return self.hosting_service

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

        Type:
            bool
        """
        hosting_service = self.hosting_service

        if hosting_service:
            return hosting_service.supports_post_commit
        else:
            return self.scmtool_class.supports_post_commit

    @property
    def supports_pending_changesets(self):
        """Whether this repository supports server-aware pending changesets.

        Type:
            bool
        """
        return self.scmtool_class.supports_pending_changesets

    @cached_property
    def diffs_use_absolute_paths(self):
        """Whether or not diffs for this repository contain absolute paths.

        Some types of source code management systems generate diffs that
        contain paths relative to the directory where the diff was generated.
        Most contain absolute paths. This flag indicates which path format
        this repository can expect.

        Type:
            bool
        """
        # Ideally, we won't have to instantiate the class, as that can end up
        # performing some expensive calls or HTTP requests.  If the SCMTool is
        # modern (doesn't define a get_diffs_use_absolute_paths), it will have
        # all the information we need on the class. If not, we might have to
        # instantiate it, but do this as a last resort.
        scmtool_cls = self.scmtool_class

        if isinstance(scmtool_cls.diffs_use_absolute_paths, bool):
            return scmtool_cls.diffs_use_absolute_paths
        elif hasattr(scmtool_cls, 'get_diffs_use_absolute_paths'):
            # This will trigger a deprecation warning.
            return self.get_scmtool().diffs_use_absolute_paths
        else:
            return False

    def get_scmtool(self):
        """Return an instance of the SCMTool for this repository.

        Each call will construct a brand new instance. The returned value
        should be stored and used for multiple operations in a single session.

        Returns:
            reviewboard.scmtools.core.SCMTool:
            A new instance of the SCMTool for this repository.
        """
        return self.scmtool_class(self)

    def get_credentials(self):
        """Return the credentials for this repository.

        This returns a dictionary with ``username`` and ``password`` keys.
        By default, these will be the values stored for the repository,
        but if a hosting service is used and the repository doesn't have
        values for one or both of these, the hosting service's credentials
        (if available) will be used instead.

        Returns:
            dict:
            A dictionary with credentials information.
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
        """Return a hooks UUID, creating one if necessary.

        A hooks UUID is used for creating unique incoming webhook URLs,
        allowing services to communicate information to Review Board.

        If a hooks UUID isn't already saved, then this will try to generate one
        that doesn't conflict with any other registered hooks UUID. It will try
        up to ``max_attempts`` times, and if it fails, ``None`` will be
        returned.

        Args:
            max_attempts (int, optional):
                The maximum number of UUID generation attempts to try before
                giving up.

        Returns:
            unicode:
            The resulting UUID.

        Raises:
            Exception:
                The maximum number of attempts has been reached.
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

    def get_encoding_list(self):
        """Return a list of candidate text encodings for files.

        This will return a list based on a comma-separated list of encodings
        in :py:attr:`encoding`. If no encodings are configured, the default
        of ``iso-8859-15`` will be used.

        Returns:
            list of unicode:
            The list of text encodings to try for files in the repository.
        """
        encodings = []

        for e in self.encoding.split(','):
            e = e.strip()

            if e:
                encodings.append(e)

        return encodings or [self.FALLBACK_ENCODING]

    def get_file(self, path, revision, base_commit_id=None, request=None):
        """Return a file from the repository.

        This will attempt to retrieve the file from the repository. If the
        repository is backed by a hosting service, it will go through that.
        Otherwise, it will attempt to directly access the repository.

        This will send the
        :py:data:`~reviewboard.scmtools.signals.fetching_file` signal before
        beginning a file fetch from the repository (if not cached), and the
        :py:data:`~reviewboard.scmtools.signals.fetched_file` signal after.

        Args:
            path (unicode):
                The path to the file in the repository.

            revision (unicode):
                The revision of the file to retrieve.

            base_commit_id (unicode, optional):
                The ID of the commit containing the revision of the file
                to retrieve. This is required for some types of repositories
                where the revision of a file and the ID of a commit differ.

            request (django.http.HttpRequest, optional):
                The current HTTP request from the client. This is used for
                logging purposes.

        Returns:
            bytes:
            The resulting file contents.

        Raises:
            TypeError:
                One or more of the provided arguments is an invalid type.
                Details are contained in the error message.
        """
        # We wrap the result of get_file in a list and then return the first
        # element after getting the result from the cache. This prevents the
        # cache backend from converting to unicode, since we're no longer
        # passing in a string and the cache backend doesn't recursively look
        # through the list in order to convert the elements inside.
        #
        # Basically, this fixes the massive regressions introduced by the
        # Django unicode changes.
        if not isinstance(path, six.text_type):
            raise TypeError('"path" must be a Unicode string, not %s'
                            % type(path))

        if not isinstance(revision, six.text_type):
            raise TypeError('"revision" must be a Unicode string, not %s'
                            % type(revision))

        if (base_commit_id is not None and
            not isinstance(base_commit_id, six.text_type)):
            raise TypeError('"base_commit_id" must be a Unicode string, '
                            'not %s'
                            % type(base_commit_id))

        return cache_memoize(
            self._make_file_cache_key(path, revision, base_commit_id),
            lambda: [self._get_file_uncached(path, revision, base_commit_id,
                                             request)],
            large_data=True)[0]

    def get_file_exists(self, path, revision, base_commit_id=None,
                        request=None):
        """Return whether or not a file exists in the repository.

        If the repository is backed by a hosting service, this will go
        through that. Otherwise, it will attempt to directly access the
        repository.

        The result of this call will be cached, making future lookups
        of this path and revision on this repository faster.

        This will send the
        :py:data:`~reviewboard.scmtools.signals.checking_file_exists` signal
        before beginning a file fetch from the repository (if not cached), and
        the :py:data:`~reviewboard.scmtools.signals.checked_file_exists` signal
        after.

        Args:
            path (unicode):
                The path to the file in the repository.

            revision (unicode);
                The revision of the file to check.

            base_commit_id (unicode, optional):
                The ID of the commit containing the revision of the file
                to check. This is required for some types of repositories
                where the revision of a file and the ID of a commit differ.

            request (django.http.HttpRequest, optional):
                The current HTTP request from the client. This is used for
                logging purposes.

        Returns:
            bool:
            ``True`` if the file exists in the repository. ``False`` if it
            does not.

        Raises:
            TypeError:
                One or more of the provided arguments is an invalid type.
                Details are contained in the error message.
        """
        if not isinstance(path, six.text_type):
            raise TypeError('"path" must be a Unicode string, not %s'
                            % type(path))

        if not isinstance(revision, six.text_type):
            raise TypeError('"revision" must be a Unicode string, not %s'
                            % type(revision))

        if (base_commit_id is not None and
            not isinstance(base_commit_id, six.text_type)):
            raise TypeError('"base_commit_id" must be a Unicode string, '
                            'not %s'
                            % type(base_commit_id))

        key = self._make_file_exists_cache_key(path, revision, base_commit_id)

        if cache.get(make_cache_key(key)) == '1':
            return True

        exists = self._get_file_exists_uncached(path, revision,
                                                base_commit_id, request)

        if exists:
            cache_memoize(key, lambda: '1')

        return exists

    def get_branches(self):
        """Return a list of all branches on the repository.

        This will fetch a list of all known branches for use in the API and
        New Review Request page.

        Returns:
            list of reviewboard.scmtools.core.Branch:
            The list of branches in the repository. One (and only one) will
            be marked as the default branch.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                The hosting service backing the repository encountered an
                error.

            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.

            NotImplementedError:
                Branch retrieval is not available for this type of repository.
        """
        hosting_service = self.hosting_service

        cache_key = make_cache_key('repository-branches:%s' % self.pk)

        if hosting_service:
            branches_callable = lambda: hosting_service.get_branches(self)
        else:
            branches_callable = self.get_scmtool().get_branches

        return cache_memoize(cache_key, branches_callable,
                             self.BRANCHES_CACHE_PERIOD)

    def get_commit_cache_key(self, commit_id):
        """Return the cache key used for a commit ID.

        The resulting cache key is used to cache information about a commit
        retrieved from the repository that matches the provided ID. This can
        be used to delete information already in cache.

        Args:
            commit_id (unicode):
                The ID of the commit to generate a cache key for.

        Returns:
            unicode:
            The resulting cache key.
        """
        return 'repository-commit:%s:%s' % (self.pk, commit_id)

    def get_commits(self, branch=None, start=None):
        """Return a list of commits.

        This will fetch a batch of commits from the repository for use in the
        API and New Review Request page.

        The resulting commits will be in order from newest to oldest, and
        should return upwards of a fixed number of commits (usually 30, but
        this depends on the type of repository and its limitations). It may
        also be limited to commits that exist on a given branch (if supported
        by the repository).

        This can be called multiple times in succession using the
        :py:attr:`Commit.parent` of the last entry as the ``start`` parameter
        in order to paginate through the history of commits in the repository.

        Args:
            branch (unicode, optional):
                The branch to limit commits to. This may not be supported by
                all repositories.

            start (unicode, optional):
                The commit to start at. If not provided, this will fetch the
                first commit in the repository.

        Returns:
            list of reviewboard.scmtools.core.Commit:
            The retrieved commits.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                The hosting service backing the repository encountered an
                error.

            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.

            NotImplementedError:
                Commits retrieval is not available for this type of repository.
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
        """Return an individual change/commit in the repository.

        Args:
            revision (unicode):
                The commit ID or revision to retrieve.

        Returns:
            reviewboard.scmtools.core.Commit:
            The commit from the repository.

        Raises:
            reviewboard.hostingsvcs.errors.HostingServiceError:
                The hosting service backing the repository encountered an
                error.

            reviewboard.scmtools.errors.SCMError:
                The repository tool encountered an error.

            NotImplementedError:
                Commits retrieval is not available for this type of repository.
        """
        hosting_service = self.hosting_service

        if hosting_service:
            return hosting_service.get_change(self, revision)
        else:
            return self.get_scmtool().get_change(revision)

    def normalize_patch(self, patch, filename, revision):
        """Normalize a diff/patch file before it's applied.

        This can be used to take an uploaded diff file and modify it so that
        it can be properly applied. This may, for instance, uncollapse
        keywords or remove metadata that would confuse :command:`patch`.

        This passes the request on to the hosting service or repository
        tool backend.

        Args:
            patch (bytes):
                The diff/patch file to normalize.

            filename (unicode):
                The name of the file being changed in the diff.

            revision (unicode):
                The revision of the file being changed in the diff.

        Returns:
            bytes:
            The resulting diff/patch file.
        """
        hosting_service = self.hosting_service

        if hosting_service:
            return hosting_service.normalize_patch(repository=self,
                                                   patch=patch,
                                                   filename=filename,
                                                   revision=revision)
        else:
            return self.get_scmtool().normalize_patch(patch=patch,
                                                      filename=filename,
                                                      revision=revision)

    def is_accessible_by(self, user):
        """Return whether or not the user has access to the repository.

        The repository is accessibly by the user if it is public or
        the user has access to it (either by being explicitly on the allowed
        users list, or by being a member of a review group on that list).

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            ``True`` if the repository is accessible by the user.
            ``False`` if it is not.
        """
        if self.local_site and not self.local_site.is_accessible_by(user):
            return False

        return (self.public or
                user.is_superuser or
                (user.is_authenticated() and
                 (self.review_groups.filter(users__pk=user.pk).exists() or
                  self.users.filter(pk=user.pk).exists())))

    def is_mutable_by(self, user):
        """Return whether or not the user can modify or delete the repository.

        The repository is mutable by the user if the user is an administrator
        with proper permissions or the repository is part of a LocalSite and
        the user has permissions to modify it.

        Args:
            user (django.contrib.auth.models.User):
                The user to check.

        Returns:
            bool:
            ``True`` if the repository can modify or delete the repository.
            ``False`` if they cannot.
        """
        return user.has_perm('scmtools.change_repository', self.local_site)

    def archive(self, save=True):
        """Archive a repository.

        The repository won't appear in any public lists of repositories,
        and won't be used when looking up repositories. Review requests
        can't be posted against an archived repository.

        New repositories can be created with the same information as the
        archived repository.

        Args:
            save (bool, optional):
                Whether to save the repository immediately.
        """
        # This should be sufficiently unlikely to create duplicates. time()
        # will use up a max of 8 characters, so we slice the name down to
        # make the result fit in 64 characters
        max_name_len = self._meta.get_field('name').max_length
        encoded_time = '%x' % int(time())
        reserved_len = len('ar::') + len(encoded_time)

        self.name = 'ar:%s:%s' % (self.name[:max_name_len - reserved_len],
                                  encoded_time)
        self.archived = True
        self.public = False
        self.archived_timestamp = timezone.now()

        if save:
            self.save(update_fields=('name', 'archived', 'public',
                                     'archived_timestamp'))

    def save(self, **kwargs):
        """Save the repository.

        This will perform any data normalization needed, and then save the
        repository to the database.

        Args:
            **kwargs (dict):
                Keyword arguments to pass to the parent method.
        """
        # Prevent empty strings from saving in the admin UI, which could lead
        # to database-level validation errors.
        if self.hooks_uuid == '':
            self.hooks_uuid = None

        return super(Repository, self).save(**kwargs)

    def clean(self):
        """Clean method for checking null unique_together constraints.

        Django has a bug where unique_together constraints for foreign keys
        aren't checked properly if one of the relations is null. This means
        that users who aren't using local sites could create multiple groups
        with the same name.

        Raises:
            django.core.exceptions.ValidationError:
                Validation of the model's data failed. Details are in the
                exception.
        """
        super(Repository, self).clean()

        if self.local_site is None:
            existing_repos = (
                Repository.objects
                .exclude(pk=self.pk)
                .filter(Q(name=self.name) |
                        (Q(archived=False) &
                         Q(path=self.path)))
                .values('name', 'path')
            )

            errors = {}

            for repo_info in existing_repos:
                if repo_info['name'] == self.name:
                    errors['name'] = [
                        ValidationError(self.NAME_CONFLICT_ERROR,
                                        code='repository_name_exists'),
                    ]

                if repo_info['path'] == self.path:
                    errors['path'] = [
                        ValidationError(self.PATH_CONFLICT_ERROR,
                                        code='repository_path_exists'),
                    ]

            if errors:
                raise ValidationError(errors)

    def _make_file_cache_key(self, path, revision, base_commit_id):
        """Return a cache key for fetched files.

        Args:
            path (unicode):
                The path to the file in the repository.

            revision (unicode):
                The revision of the file.

            base_commit_id (unicode):
                The ID of the commit containing the revision of the file.
                This is required for some types of repositories where the
                revision of a file and the ID of a commit differ.

        Returns:
            unicode:
            A cache key representing this file.
        """
        return 'file:%s:%s:%s:%s:%s' % (
            self.pk,
            urlquote(path),
            urlquote(revision),
            urlquote(base_commit_id or ''),
            urlquote(self.raw_file_url or ''))

    def _make_file_exists_cache_key(self, path, revision, base_commit_id):
        """Makes a cache key for file existence checks.

        Args:
            path (unicode):
                The path to the file in the repository.

            revision (unicode);
                The revision of the file to check.

            base_commit_id (unicode, optional):
                The ID of the commit containing the revision of the file
                to check. This is required for some types of repositories
                where the revision of a file and the ID of a commit differ.

        Returns:
            unicode:
            A cache key representing this file check.
        """
        return 'file-exists:%s:%s:%s:%s:%s' % (
            self.pk,
            urlquote(path),
            urlquote(revision),
            urlquote(base_commit_id or ''),
            urlquote(self.raw_file_url or ''))

    def _get_file_uncached(self, path, revision, base_commit_id, request):
        """Return a file from the repository, bypassing cache.

        This is called internally by :py:meth:`get_file` if the file isn't
        already in the cache.

        This will send the
        :py:data:`~reviewboard.scmtools.signals.fetching_file` signal before
        beginning a file fetch from the repository, and the
        :py:data:`~reviewboard.scmtools.signals.fetched_file` signal after.

        Args:
            path (unicode):
                The path to the file in the repository.

            revision (unicode):
                The revision of the file to retrieve.

            base_commit_id (unicode, optional):
                The ID of the commit containing the revision of the file
                to retrieve. This is required for some types of repositories
                where the revision of a file and the ID of a commit differ.

            request (django.http.HttpRequest, optional):
                The current HTTP request from the client. This is used for
                logging purposes.

        Returns:
            bytes:
            The resulting file contents.

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

            assert isinstance(data, bytes), (
                '%s.get_file() must return a byte string, not %s'
                % (type(hosting_service).__name__, type(data)))
        else:
            tool = self.get_scmtool()
            data = tool.get_file(path, revision,
                                 base_commit_id=base_commit_id)

            assert isinstance(data, bytes), (
                '%s.get_file() must return a byte string, not %s'
                % (type(tool).__name__, type(data)))

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
        """Check for file existence, bypassing cache.

        This is called internally by :py:meth:`get_file_exists` if the file
        isn't already in the cache.

        This function is smart enough to check if the file exists in cache,
        and will use that for the result instead of making a separate call.

        This will send the
        :py:data:`~reviewboard.scmtools.signals.checking_file_exists` signal
        before beginning a file fetch from the repository, and the
        :py:data:`~reviewboard.scmtools.signals.checked_file_exists` signal
        after.
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
                exists = tool.file_exists(path, revision,
                                          base_commit_id=base_commit_id)

            checked_file_exists.send(sender=self,
                                     path=path,
                                     revision=revision,
                                     base_commit_id=base_commit_id,
                                     request=request,
                                     exists=exists)

        return exists

    def __str__(self):
        """Return a string representation of the repository.

        This uses the repository's name as the string representation. However,
        it should not be used if explicitly wanting to retrieve the repository
        name, as future versions may return a different value.

        Returns:
            unicode:
            The repository name.
        """
        return self.name

    class Meta:
        db_table = 'scmtools_repository'
        unique_together = (('name', 'local_site'),
                           ('archived_timestamp', 'path', 'local_site'),
                           ('hooks_uuid', 'local_site'))
        verbose_name = _('Repository')
        verbose_name_plural = _('Repositories')
