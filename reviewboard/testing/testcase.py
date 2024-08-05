"""Base test case support for Review Board."""

from __future__ import annotations

import os
import re
import warnings
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import (Any, Callable, Dict, Iterator, List, Optional, Sequence,
                    TYPE_CHECKING, Tuple, Type, Union)
from uuid import uuid4

import kgb
from django.contrib.auth.models import AnonymousUser, Permission, User
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.cache import cache
from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.test.client import RequestFactory
from django.urls import ResolverMatch
from django.utils.timezone import now
from djblets.registries.errors import AlreadyRegisteredError, ItemLookupError
from djblets.secrets.token_generators import token_generator_registry
from djblets.testing.testcases import (FixturesCompilerMixin,
                                       TestCase as DjbletsTestCase)
from djblets.util.symbols import UNSET, Unsettable
from oauthlib.common import generate_token
from oauth2_provider.models import AccessToken

import reviewboard.scmtools
from reviewboard import initialize
from reviewboard.accounts.models import LocalSiteProfile, ReviewRequestVisit
from reviewboard.admin.siteconfig import load_site_config
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.certs.cert import (Certificate,
                                    CertificateBundle,
                                    CertificateFingerprints)
from reviewboard.diffviewer.differ import DiffCompatVersion
from reviewboard.diffviewer.models import (DiffCommit, DiffSet, DiffSetHistory,
                                           FileDiff)
from reviewboard.notifications.models import WebHookTarget
from reviewboard.oauth.models import Application
from reviewboard.reviews.models import (Comment,
                                        FileAttachmentComment,
                                        GeneralComment,
                                        Group,
                                        Review,
                                        ReviewRequest,
                                        ReviewRequestDraft,
                                        Screenshot,
                                        ScreenshotComment,
                                        StatusUpdate)
from reviewboard.scmtools import scmtools_registry
from reviewboard.scmtools.errors import FileNotFoundError
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.site.models import LocalSite
from reviewboard.testing.scmtool import (TestTool,
                                         TestToolSupportsPendingChangeSets,
                                         TestToolDiffX)
from reviewboard.webapi.models import WebAPIToken

if TYPE_CHECKING:
    from django.http import HttpRequest
    from djblets.db.query_comparator import ExpectedQuery
    from djblets.util.typing import JSONDict

    from reviewboard.changedescs.models import ChangeDescription
    from reviewboard.scmtools.core import FileLookupContext, RevisionID


_static_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..',
                                            'static'))


class TestCase(FixturesCompilerMixin, DjbletsTestCase):
    """The base class for Review Board test cases.

    This class provides a number of convenient functions for creating
    common objects for testing, such as review requests and comments. They're
    populated with default data that can be overridden by the callers.

    This also overcomes an annoyance with default Django unit tests where
    the cache is not cleared across tests, leading to inconsistent results
    and useless testing.
    """
    local_site_name = 'local-site-1'
    local_site_id = 1

    maxDiff = 1000000

    ws_re = re.compile(r'\s+')

    DEFAULT_FILEDIFF_DATA_DIFF = (
        b'--- README\trevision 123\n'
        b'+++ README\trevision 123\n'
        b'@@ -1 +1 @@\n'
        b'-Hello, world!\n'
        b'+Hello, everybody!\n'
    )

    DEFAULT_GIT_FILEDIFF_DATA_DIFF = (
        b'diff --git a/README b/README\n'
        b'index 94bdd3e..197009f 100644\n'
        b'--- README\n'
        b'+++ README\n'
        b'@@ -2 +2 @@\n'
        b'-blah blah\n'
        b'+blah!\n'
    )

    DEFAULT_GIT_README_DIFF = (
        b'diff --git a/readme b/readme\n'
        b'index d6613f5..5b50866 100644\n'
        b'--- a/readme\n'
        b'+++ b/readme\n'
        b'@@ -1 +1,3 @@\n'
        b'Hello there\n'
        b'+\n'
        b'+Oh hi!\n'
    )

    DEFAULT_GIT_FILEMODE_DIFF = (
        b'diff --git a/testing b/testing\n'
        b'old mode 100755\n'
        b'new mode 100644\n'
        b'index e69de29..bcae657\n'
        b'--- a/testing\n'
        b'+++ b/testing\n'
        b'@@ -0,0 +1 @@\n'
        b'+ADD\n'
        b'diff --git a/testing2 b/testing2\n'
        b'old mode 100644\n'
        b'new mode 100755\n'
    )

    DEFAULT_GIT_FILE_NOT_FOUND_DIFF = (
        b'diff --git a/missing-file b/missing-file\n'
        b'index d6613f0..5b50866 100644\n'
        b'--- a/missing-file\n'
        b'+++ b/missing-file\n'
        b'@@ -1 +1,3 @@\n'
        b'Hello there\n'
        b'+\n'
        b'+Oh hi!\n'
    )

    DEFAULT_GIT_BINARY_IMAGE_DIFF = (
        b'diff --git a/logo.png b/logo.png\n'
        b'index 86b520c..86b520d\n'
        b'Binary files a/logo.png and b/logo.png differ\n'
    )

    @classmethod
    def setUpClass(cls):
        """Set up the test class."""
        orig_fixtures = cls.fixtures

        if orig_fixtures and 'test_scmtools' in orig_fixtures:
            # Avoid a warning due to the empty fixture. We want to remove it
            # from the list in the parent setUpClass(), but keep it for the
            # later call to _fixture_setup().
            cls.fixtures = list(orig_fixtures)
            cls.fixtures.remove('test_scmtools')

        super().setUpClass()

        cls.fixtures = orig_fixtures

        # Add any test SCMTools to the registry
        try:
            scmtools_registry.register(TestTool)
            scmtools_registry.register(TestToolSupportsPendingChangeSets)
            scmtools_registry.register(TestToolDiffX)
        except AlreadyRegisteredError:
            # When running an individual test case that uses the test_scmtools
            # fixture, these will already be present in the registry. Ignore
            # this case.
            pass

    @classmethod
    def tearDownClass(cls):
        """Tear down the test class."""
        super().tearDownClass()

        try:
            scmtools_registry.unregister(TestTool)
            scmtools_registry.unregister(TestToolSupportsPendingChangeSets)
            scmtools_registry.unregister(TestToolDiffX)
        except ItemLookupError:
            pass

    def setUp(self):
        super(TestCase, self).setUp()

        initialize(load_extensions=False)

        self._local_sites = {}

        # Clear the cache so that previous tests don't impact this one.
        cache.clear()

    def load_fixtures(self, fixtures, **kwargs):
        """Load data from fixtures.

        If the legacy ``test_scmtools`` fixture is used, the SCMTools
        registry will re-synchronize with the database, adding any missing
        tools.

        Args:
            fixtures (list of str):
                The list of fixtures to load.

            **kwargs (dict):
                Additional keyword arguments to pass to the parent method.
        """
        if fixtures and 'test_scmtools' in fixtures:
            fixtures = list(fixtures)
            fixtures.remove('test_scmtools')

            scmtools_registry.populate_db()

        super().load_fixtures(fixtures, **kwargs)

    def shortDescription(self):
        """Returns the description of the current test.

        This changes the default behavior to replace all newlines with spaces,
        allowing a test description to span lines. It should still be kept
        short, though.
        """
        doc = self._testMethodDoc

        if doc is not None:
            doc = doc.split('\n\n', 1)[0]
            doc = self.ws_re.sub(' ', doc).strip()

        return doc

    def get_local_site_or_none(
        self,
        name: Optional[str],
    ) -> Optional[LocalSite]:
        """Return a LocalSite matching the name, if provided, or None.

        Args:
            name (str):
                The name of the Local Site.

        Returns:
            reviewboard.site.models.LocalSite:
            The Local Site, or ``None`` if ``name`` is ``None``.

        Raises:
            django.core.exceptions.ObjectDoesNotExist:
                The Local Site was specified but could not be found.
        """
        if name:
            return self.get_local_site(name=name)
        else:
            return None

    def get_local_site(
        self,
        name: str,
    ) -> LocalSite:
        """Return a LocalSite matching the name, if provided.

        The Local Site will be cached for future lookups in the test.

        Args:
            name (str):
                The name of the Local Site.

        Returns:
            reviewboard.site.models.LocalSite:
            The Local Site.

        Raises:
            django.core.exceptions.ObjectDoesNotExist:
                The Local Site could not be found.
        """
        if name not in self._local_sites:
            self._local_sites[name] = LocalSite.objects.get(name=name)

        return self._local_sites[name]

    def create_local_site(
        self,
        name: str = local_site_name,
        *,
        users: Sequence[User] = [],
        admins: Sequence[User] = [],
        **kwargs,
    ) -> LocalSite:
        """Create a LocalSite for testing.

        To maintain compatibility with the behavior of the ``test_site``
        fixture, this will cache the created LocalSite for use in
        :py:meth:`get_local_site`.

        Version Changed:
            5.0.7:
            * Added ``users`` and ``admins`` arguments.

        Version Added:
            5.0

        Args:
            name (str, optional):
                The local site name. This defaults to
                :py:attr:`local_site_name`.

            users (list of django.contrib.auth.models.User, optional):
                A list of users to add to the site.

                Version Added:
                    5.0.7

            admins (list of django.contrib.auth.models.User, optional):
                A list of users to add to the site's list of administrators.

                Version Added:
                    5.0.7

            **kwargs (dict):
                Keyword arguments to be passed to the
                :py:class:`~reviewboard.site.models.LocalSite` initializer.

        Returns:
            reviewboard.site.models.LocalSite:
            The resulting LocalSite.
        """
        assert name not in self._local_sites, (
            'LocalSite "%s" has already been created' % name)

        local_site = LocalSite.objects.create(name=name, **kwargs)
        self._local_sites[name] = local_site

        if users:
            local_site.users.add(*users)

        if admins:
            local_site.admins.add(*admins)

        return local_site

    def create_http_request(
        self,
        path: str = '/',
        user: Optional[Union[AnonymousUser, User]] = None,
        method: str = 'get',
        with_local_site: bool = False,
        local_site: Optional[LocalSite] = None,
        resolver_match: Optional[ResolverMatch] = None,
        view: Optional[Callable[..., Any]] = None,
        url_name: Optional[str] = None,
        **kwargs,
    ) -> HttpRequest:
        """Create an HttpRequest for testing.

        This wraps :py:class:`~django.test.client.RequestFactory`,
        automatically handing some common fields normally set by middleware,
        including the user, resolver match, and Local Site.

        Version Changed:
            6.0:
            Added the ``url_name`` parameter.

        Args:
            path (str, optional):
                The path for the HTTP request, relative to the server root.

            user (django.contrib.auth.models.User, optional):
                The user authenticated for the request. If not provided,
                :py:class:`~django.contrib.auth.models.AnonymousUser` will
                be used.

            method (str, optional):
                The method on :py:class:`~django.test.client.RequestFactory`
                used to create the request.

            with_local_site (bool, optional):
                If set, the default Local Site will be assigned to the
                request, if ``local_site`` is not provided in the call.

            local_site (reviewboard.site.models.LocalSite, optional):
                The Local Site to assign to the request.

            resolver_match (django.urls.ResolverMatch, optional):
                A custom resolver match to set for the request. This may be
                used by views to determine which URL entry was invoked. If
                not provided, a blank one pointing to the provided ``view``
                will be used.

            view (callable, optional):
                The view used for a default
                :py:class:`~django.urls.ResolverMatch`.

            url_name (str, optional):
                The URL name to set in the resolver match, when creating one.
                If ``resolver_match`` is passed in, this will not be used.

                Version Added:
                    6.0

            **kwargs (dict):
                Additional keyword arguments to pass to the request factory
                method.

        Returns:
            django.http.HttpRequest:
            The resulting HTTP request.

        Raises:
            ValueError:
                One or more of the values provided was invalid.
        """
        factory = RequestFactory()

        try:
            factory_method = getattr(factory, method)
        except AttributeError:
            raise ValueError('Invalid RequestFactory method "%s"' % method)

        if local_site is None:
            if with_local_site:
                local_site_name = self.local_site_name
                local_site = self.get_local_site(name=local_site_name)
            else:
                local_site_name = None
                local_site = None
        else:
            local_site_name = local_site.name

        if resolver_match is None:
            resolver_match = ResolverMatch(
                func=view or (lambda *args, **kwargs: None),
                args=(),
                kwargs={},
                url_name=url_name)

        request: HttpRequest = factory_method(path, **kwargs)
        request.local_site = local_site  # type: ignore
        request._local_site_name = local_site_name
        request.resolver_match = resolver_match
        request.user = user or AnonymousUser()

        middleware = SessionMiddleware(
            MessageMiddleware(
                lambda request: HttpResponse('')))
        middleware(request)

        return request

    def create_user(
        self,
        username: str = 'test-user',
        password: str = '',
        email: str = 'test@example.com',
        perms: Optional[Sequence[Tuple[str, str]]] = None,
        **kwargs,
    ) -> User:
        """Create a User for testing.

        Args:
            username (str, optional):
                The username.

            password (str, optional):
                The user's password.

            email (str, optional):
                The user's e-mail address.

            perms (list of tuple, optional):
                A list of permissions to assign. Each item is a tuple
                of ``(app_label, permission_name)``.

            **kwargs (dict):
                Additional attributes for the user.

        Returns:
            django.contrib.auth.models.User:
            The new User object.
        """
        user = User(username=username,
                    email=email,
                    **kwargs)

        if password:
            user.set_password(password)

        user.save()

        if perms:
            user.user_permissions.add(*[
                Permission.objects.get(codename=perm_name,
                                       content_type__app_label=perm_app_label)
                for perm_app_label, perm_name in perms
            ])

        return user

    def create_webapi_token(
        self,
        user: User,
        note: str = 'Sample note',
        policy: JSONDict = {'access': 'rw'},
        with_local_site: bool = False,
        token_generator_id: Optional[str] = None,
        token_info: JSONDict = {'token_type': 'rbp'},
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> WebAPIToken:
        """Create a WebAPIToken for testing.

        Version Changed:
            5.0:
            * Added the ``local_site``, ``token_generator_id`` and
              ``token_info`` parameters. The latter are used to specify the
              type of token to generate.

        Args:
            user (django.contrib.auth.models.User):
                The user who owns the token.

            note (str, optional):
                A note describing the token.

            policy (dict, optional):
                The policy document describing what this token can access
                in the API.

            with_local_site (bool, optional):
                Whether to create the repository using a Local Site. This
                will choose one based on :py:attr:`local_site_name`.

                If ``local_site`` is provided, this argument is ignored.

            token_generator_id (str, optional):
                The ID of the token generator to use for generating the token.
                If not set this will use the default token generator that is
                defined in the token generator registry.

                Version Added:
                    5.0

            token_info (dict, optional):
                A dictionary that contains information needed for token
                generation. If not set this will default to a dictionary
                that contains a ``token_type`` value.

                Version Added:
                    5.0

            local_site (reviewboard.site.models.LocalSite, optional):
                The explicit Local Site to attach.

                Version Added:
                    5.0

            **kwargs (dict):
                Keyword arguments to be passed to
                :py:meth:`~djblets.webapi.managers.WebAPITokenManager.
                generate_token`.

        Returns:
            reviewboard.webapi.models.WebAPIToken:
            The WebAPIToken that was created.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(name=self.local_site_name)
            else:
                local_site = None

        if token_generator_id is None:
            token_generator_id = \
                token_generator_registry.get_default().token_generator_id

        return WebAPIToken.objects.generate_token(
            user=user,
            note=note,
            policy=policy,
            local_site=local_site,
            token_generator_id=token_generator_id,
            token_info=token_info,
            **kwargs)

    @contextmanager
    def assertQueries(
        self,
        queries: Sequence[Union[ExpectedQuery,
                                Dict[str, Any]]],
        num_statements: Optional[int] = None,
        *,
        with_tracebacks: bool = False,
        traceback_size: int = 15,
        check_join_types: Optional[bool] = True,
        check_subqueries: Optional[bool] = True,
    ) -> Iterator[None]:
        """Assert the number and complexity of queries.

        This is a wrapper around :py:meth:`assertQueries()
        <djblets.testing.testcases.TestCase.assertQueries>` in Djblets that
        forces an opt-in to checking join types and subqueries.

        This wrapper can go away when those are enabled by default.

        Version Added:
            5.0.7

        Args:
            queries (list of ExpectedQuery):
                The list of query dictionaries to compare executed queries
                against.

            num_statements (int, optional):
                The number of SQL statements executed.

                This defaults to the length of ``queries``, but callers may
                need to provide an explicit number, as some operations may add
                additional database-specific statements (such as
                transaction-related SQL) that won't be covered in ``queries``.

            with_tracebacks (bool, optional):
                If enabled, tracebacks for queries will be included in
                results.

            tracebacks_size (int, optional):
                The size of any tracebacks, in number of lines.

                The default is 15.

            check_join_types (bool, optional):
                Whether to check join types.

                If enabled, table join types (``join_types`` on queries) will
                be checked. This is currently disabled by default, in order
                to avoid breaking tests, but will be enabled by default in
                Djblets 5.

            check_subqueries (bool, optional):
                Whether to check subqueries.

                If enabled, ``inner_query`` on queries with subqueries will
                be checked. This is currently disabled by default, in order
                to avoid breaking tests, but will be enabled by default in
                Djblets 5.

        Raises:
            AssertionError:
                The parameters passed, or the queries compared, failed
                expectations.
        """
        with super().assertQueries(queries=queries,
                                   num_statements=num_statements,
                                   with_tracebacks=with_tracebacks,
                                   traceback_size=traceback_size,
                                   check_join_types=check_join_types,
                                   check_subqueries=check_subqueries):
            yield

    @contextmanager
    def assert_warns(
        self,
        cls: Type[DeprecationWarning] = DeprecationWarning,
        message: Optional[str] = None,
    ) -> Iterator[None]:
        """A context manager for asserting code generates a warning.

        This will check that the code ran in the context will generate a
        warning with the given class and message. If the call generates
        multiple warnings, each will be checked.

        Args:
            cls (type, optional):
                The type of warning that should be generated.

            message (str, optional):
                The message that should be generated in the warning.

        Context:
            The code to run that's expected to generate a warning.
        """
        with warnings.catch_warnings(record=True) as w:
            # Some warnings such as DeprecationWarning are filtered by
            # default, stop filtering them.
            warnings.simplefilter('always')

            # Now that we've done that, some warnings may come in that we
            # really don't want. We want to turn those back off.
            try:
                from django.utils.deprecation import RemovedInDjango20Warning
                warnings.filterwarnings('ignore',
                                        category=RemovedInDjango20Warning)
            except ImportError:
                pass

            self.assertEqual(len(w), 0)

            yield

            warning_found = any(
                (issubclass(warning.category, cls) and
                 message == str(warning.message))
                for warning in w
            )

            if not warning_found:
                self.fail('No warning was found matching type %r and message '
                          '%r'
                          % (cls, message))

    def create_diff_file_attachment(
        self,
        filediff: FileDiff,
        from_modified: bool = True,
        review_request: Optional[ReviewRequest] = None,
        orig_filename: str = 'filename.png',
        caption: str = 'My Caption',
        mimetype: str = 'image/png',
        **kwargs,
    ) -> FileAttachment:
        """Create a diff-based FileAttachment for testing.

        The FileAttachment is tied to the given FileDiff. It's populated
        with default data that can be overridden by the caller.

        Args:
            filediff (reviewboard.diffviewer.models.filediff.FileDiff):
                The FileDiff that the attachment is associated with.

            from_modified (bool, optional):
                Whether this file attachment is associated with the modified
                version of the file.

            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest, optional):
                The optional review request that owns this file attachment.

            orig_filename (str, optional):
                The original filename as shown in the diff.

            caption (str, optional):
                The caption of the file.

            mimetype (str, optional):
                The file's mimetype.

            **kwargs (dict):
                Additional model attributes to set on the file attachment.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The newly-created file attachment.
        """
        file_attachment = FileAttachment.objects.create_from_filediff(
            filediff=filediff,
            from_modified=from_modified,
            caption=caption,
            orig_filename=orig_filename,
            mimetype=mimetype,
            **kwargs)

        filename = os.path.join(_static_root, 'rb', 'images', 'logo.png')

        with open(filename, 'rb') as f:
            file_attachment.file.save(os.path.basename(filename), File(f),
                                      save=True)

        if review_request:
            review_request.file_attachments.add(file_attachment)

        return file_attachment

    def create_diffcommit(
        self,
        repository: Optional[Repository] = None,
        diffset: Optional[DiffSet] = None,
        commit_id: str = 'r1',
        parent_id: str = 'r0',
        diff_contents: bytes = DEFAULT_GIT_FILEDIFF_DATA_DIFF,
        parent_diff_contents: Optional[bytes] = None,
        author_name: str = 'Author',
        author_email: str = 'author@example.com',
        author_date: Optional[datetime] = None,
        commit_message: str = 'Commit message',
        committer_name: str = 'Committer',
        committer_email: str = 'committer@example.com',
        committer_date: Optional[datetime] = None,
        with_diff: bool = True,
        extra_data: Optional[JSONDict] = None,
        **kwargs,
    ) -> DiffCommit:
        """Create a DiffCommit for testing.

        By default, this also parses the provided diff data and creates a
        :py:class:`reviewboard.diffviewer.models.filediff.FileDiff` attached to
        the commit. Callers can turn this off using ``with_diff=False``.

        Version Changed:
            4.0.5:
            Added the ``with_diff`` and ``extra_data`` options.

        Args:
            repository (reviewboard.scmtools.models.Repository, optional):
                The repository the commit is associated with.

            diffset (reviewboard.diffviewer.models.diffset.DiffSet, optional):
                The parent diffset.

            commit_id (str, optional):
                The commit ID.

            parent_id (str, optional):
                The commit ID of the parent commit.

            diff_contents (bytes, optional):
                The contents of the diff.

            parent_diff_contents (bytes, optional):
                The contents of the parent diff, if any.

            author_name (str, optional):
                The name of the commit's author.

            author_email (str, optional):
                The e-mail address of the commit's author.

            author_date (datetime.datetime, optional):
                The date the commit was authored.

            commit_message (str, optional):
                The commit message.

            committer_name (str, optional):
                The name of the committer, if any.

            committer_email (str, optional):
                The e-mail address of the committer, if any.

            committer_date (datetime.datetime, optional):
                The date the commit was committed, if any.

            with_diff (bool, optional):
                Whether to create this with a diff.

                If ``True`` (the default), this will also create a
                :py:class:`~reviewboard.diffviewer.models.filediff.FileDiff`
                based on ``diff_contents`` and ``parent_diff_contents``.
                The diffs will be parsed using the repository's tool's native
                parser in order to create the commit.

                If ``False``, this will just create the object in the
                database.

            extra_data (dict, optional):
                Explicit extra_data to attach to the commit.

            **kwargs (dict):
                Keyword arguments to be passed to the
                :py:class:`~reviewboard.diffviewer.models.diffcommit.
                DiffCommit` initializer.

        Returns:
            reviewboard.diffviewer.models.diffcommit.DiffCommit:
            The resulting DiffCommit.
        """
        assert isinstance(diff_contents, bytes)

        if diffset is None:
            diffset = self.create_diffset(repository=repository)
        else:
            repository = diffset.repository

        if author_date is None:
            author_date = now()

        if not committer_date and committer_name and committer_email:
            committer_date = author_date

        if ((not committer_name and committer_email) or
            (committer_name and not committer_email)):
            raise ValueError(
                'Either both or neither of committer_name and committer_email '
                'must be provided.')

        if parent_diff_contents:
            assert isinstance(parent_diff_contents, bytes)
            parent_diff_file_name = 'parent_diff'
        else:
            parent_diff_file_name = None

        if with_diff:
            diff_commit = DiffCommit.objects.create_from_data(
                repository=repository,
                diff_file_name='diff',
                diff_file_contents=diff_contents,
                parent_diff_file_name=parent_diff_file_name,
                parent_diff_file_contents=parent_diff_contents,
                diffset=diffset,
                commit_id=commit_id,
                parent_id=parent_id,
                author_name=author_name,
                author_email=author_email,
                author_date=author_date,
                commit_message=commit_message,
                request=None,
                committer_name=committer_name,
                committer_email=committer_email,
                committer_date=committer_date,
                check_existence=False,
                **kwargs)

            assert diff_commit is not None

            if extra_data:
                diff_commit.extra_data.update(extra_data)

            return diff_commit
        else:
            return DiffCommit.objects.create(
                diffset=diffset,
                commit_id=commit_id,
                parent_id=parent_id,
                author_name=author_name,
                author_email=author_email,
                author_date=author_date,
                commit_message=commit_message,
                committer_name=committer_name,
                committer_email=committer_email,
                committer_date=committer_date,
                **kwargs)

    def create_diffset(
        self,
        review_request: Optional[ReviewRequest] = None,
        revision: int = 1,
        repository: Optional[Repository] = None,
        draft: bool = False,
        name: str = 'diffset',
        **kwargs,
    ) -> DiffSet:
        """Create a DiffSet for testing.

        The DiffSet defaults to revision 1. This can be overridden by the
        caller.

        DiffSets generally are tied to a ReviewRequest, but it's optional.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest, optional):
                The only review request that owns the DiffSet.

            revision (int, optional):
                The revision of the DiffSet.

            repository (reviewboard.scmtools.models.Repository, optional):
                The repository that backs files in the DiffSet.

            draft (bool, optional):
                Whether this is a draft DiffSet.

            name (str, optional):
                The name of the DiffSet.

            **kwargs (dict):
                Additional model attributes to set on the DiffSet.

        Returns:
            reviewboard.diffviewer.models.diffset.DiffSet:
            The newly-created DiffSet.
        """
        if review_request:
            repository = review_request.repository

        diffset = DiffSet.objects.create(
            name=name,
            revision=revision,
            repository=repository,
            diffcompat=DiffCompatVersion.DEFAULT,
            **kwargs)

        if review_request:
            if draft:
                review_request_draft = \
                    self.create_review_request_draft(review_request)
                review_request_draft.diffset = diffset
                review_request_draft.save()
            else:
                review_request.diffset_history.diffsets.add(diffset)

        return diffset

    def create_diff_comment(
        self,
        review: Review,
        filediff: FileDiff,
        interfilediff: Optional[FileDiff] = None,
        text: str = 'My comment',
        issue_opened: bool = False,
        issue_status: Optional[str] = None,
        first_line: int = 1,
        num_lines: int = 5,
        extra_fields: Optional[JSONDict] = None,
        reply_to: Optional[Comment] = None,
        timestamp: Optional[datetime] = None,
        **kwargs,
    ) -> Comment:
        """Create a Comment for testing.

        The comment is tied to the given Review and FileDiff (and, optionally,
        an interfilediff). It's populated with default data that can be
        overridden by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review associated with the comment.

            filediff (reviewboard.diffviewer.models.filediff.FileDiff):
                The FileDiff associated with the comment.

            interfilediff (reviewboard.diffviewer.models.filediff.FileDiff,
                           optional):
                The FileDiff used for the end of an interdiff range associated
                with the comment.

            text (str):
                The text for the comment.

            issue_opened (bool, optional):
                Whether an issue is to be opened for the comment.

            issue_status (str, optional):
                The issue status to set, if an issue is opened. Defaults to
                being an open issue.

            first_line (int, optional):
                The first line (0-based) of the comment range.

            num_lines (int, optional):
                The number of lines in the comment.

            extra_fields (dict, optional):
                Extra data to set on the comment.

            reply_to (reviewboard.reviews.models.diff_comment.Comment,
                      optional):
                The comment this comment replies to.

            timestamp (datetime.datetime, optional):
                The timestamp for the comment.

                Version Added:
                    5.0

            **kwargs (dict):
                Additional model attributes to set on the comment.

        Returns:
            reviewboard.reviews.models.diff_comment.Comment:
            The resulting comment.
        """
        if issue_opened and not issue_status:
            issue_status = Comment.OPEN

        comment = Comment(
            filediff=filediff,
            interfilediff=interfilediff,
            first_line=first_line,
            num_lines=num_lines,
            text=text,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to,
            **kwargs)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.comments.add(comment)

        if timestamp:
            Comment.objects.filter(pk=comment.pk).update(timestamp=timestamp)
            comment.timestamp = timestamp

        return comment

    def create_file_attachment(
        self,
        review_request: ReviewRequest,
        attachment_history: Optional[FileAttachmentHistory] = None,
        draft: bool = False,
        active: bool = True,
        with_history: bool = True,
        **kwargs,
    ) -> FileAttachment:
        """Create a FileAttachment for testing.

        The attachment is tied to the given
        :py:class:`~reviewboard.reviews.models.review_request.ReviewRequest`.
        It's populated with default data that can be overridden by the caller.

        Version Changed:
            6.0:
            Added the ``with_history`` parameter.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request that ultimately owns the file attachment.

            attachment_history (reviewboard.attachments.models.
                                FileAttachmentHistory,
                                optional):
                An attachment history managing the file attachment.

            draft (bool or
                   reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft, optional):
                A draft to associate the attachment with. This can also be
                a boolean, for legacy reasons, which will attempt to look up
                or create a draft for the review request.

            active (bool, optional):
                Whether this attachment is considered active (not deleted).

            with_history (bool, optional):
                Whether to create a FileAttachmentHistory for this file
                attachment. If ``attachment_history`` is supplied, that
                attachment history will be used instead.

                This defaults to ``True``.

                Version Added:
                    6.0

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`create_file_attachment_base`.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The resulting file attachment.
        """
        if with_history and attachment_history is None:
            attachment_history = self.create_file_attachment_history(
                review_request)

        file_attachment = self.create_file_attachment_base(
            attachment_history=attachment_history,
            **kwargs)

        if draft:
            if isinstance(draft, ReviewRequestDraft):
                review_request_draft = draft
            else:
                review_request_draft = \
                    self.create_review_request_draft(review_request)

            if active:
                attachments = review_request_draft.file_attachments
            else:
                attachments = review_request_draft.inactive_file_attachments
        else:
            if active:
                attachments = review_request.file_attachments
            else:
                attachments = review_request.inactive_file_attachments

        attachments.add(file_attachment)

        return file_attachment

    def create_user_file_attachment(
        self,
        user: User,
        has_file: bool = False,
        **kwargs,
    ) -> FileAttachment:
        """Create a user FileAttachment for testing.

        The :py:class:`reviewboard.attachments.models.FileAttachment` is tied
        to the given :py:class:`django.contrib.auth.models.User`. It's
        populated with default data that can be overridden by the caller.
        Notably, by default the FileAttachment will be created without a file
        or a local_site.

        Args:
            user (django.contrib.auth.models.User):
                The user who owns the file attachment.

            has_file (bool, optional):
                ``True`` if an actual file object should be included in the
                model. This is ``False`` by default.

            **kwargs (dict):
                Additional keyword arguments to pass to
                :py:meth:`create_file_attachment_base`.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The new file attachment instance.
        """
        return self.create_file_attachment_base(user=user,
                                                has_file=has_file,
                                                **kwargs)

    def create_file_attachment_comment(
        self,
        review: Review,
        file_attachment: FileAttachment,
        diff_against_file_attachment: Optional[FileAttachment] = None,
        text: str = 'My comment',
        issue_opened: bool = False,
        issue_status: Optional[str] = None,
        extra_fields: Optional[JSONDict] = None,
        reply_to: Optional[FileAttachmentComment] = None,
        timestamp: Optional[datetime] = None,
        **kwargs,
    ) -> FileAttachmentComment:
        """Create a FileAttachmentComment for testing.

        The comment is tied to the given Review and FileAttachment. It's
        populated with default data that can be overridden by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review associated with the comment.

            file_attachment (reviewboard.attachments.models.FileAttachment):
                The file attachment associated with the comment.

            diff_against_file_attachment (reviewboard.attachments.models.
                                          FileAttachment, optional):
                The file attachment being diff against, for comments on
                attachment diffs.

            text (str, optional):
                The text for the comment.

            issue_opened (bool, optional):
                Whether an issue is to be opened for the comment.

            issue_status (str, optional):
                The issue status to set, if an issue is opened. Defaults to
                being an open issue.

            extra_fields (dict, optional):
                Extra data to set on the comment.

            reply_to (reviewboard.reviews.models.file_attachment_comment.
                      FileAttachmentComment, optional):
                The comment this comment replies to.

            timestamp (datetime.datetime, optional):
                The timestamp for the comment.

                Version Added:
                    5.0

            **kwargs (dict):
                Additional model attributes to set on the comment.

        Returns:
            reviewboard.reviews.models.file_attachment_comment.FileAttachmentComment:
            The resulting comment.
        """
        if issue_opened and not issue_status:
            issue_status = FileAttachmentComment.OPEN

        comment = FileAttachmentComment(
            file_attachment=file_attachment,
            diff_against_file_attachment=diff_against_file_attachment,
            text=text,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to,
            **kwargs)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.file_attachment_comments.add(comment)

        if timestamp:
            queryset = FileAttachmentComment.objects.filter(pk=comment.pk)
            queryset.update(timestamp=timestamp)
            comment.timestamp = timestamp

        return comment

    def create_file_attachment_history(
        self,
        review_request: Optional[ReviewRequest] = None,
        display_position: Optional[int] = None,
        **kwargs,
    ) -> FileAttachmentHistory:
        """Create a FileAttachmentHistory for testing.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest, optional):
                The optional review request to attach the history to.

            display_position (int, optional):
                The display position on the review request. If not provided,
                a proper position will be computed.

            **kwargs (dict):
                Additional fields to set on the model.

        Returns:
            reviewboard.attachments.models.FileAttachmentHistory:
            The new file attachment instance.
        """
        if display_position is None:
            if review_request is None:
                display_position = 0
            else:
                display_position = \
                    FileAttachmentHistory.compute_next_display_position(
                        review_request)

        attachment_history = FileAttachmentHistory.objects.create(
            display_position=display_position,
            **kwargs)

        if review_request is not None:
            review_request.file_attachment_histories.add(attachment_history)

        return attachment_history

    def create_filediff(
        self,
        diffset: DiffSet,
        source_file: str = '/test-file',
        dest_file: str = '/test-file',
        source_revision: RevisionID = '123',
        dest_detail: str = '124',
        status: str = FileDiff.MODIFIED,
        diff: bytes = DEFAULT_FILEDIFF_DATA_DIFF,
        commit: Optional[DiffCommit] = None,
        encoding: Optional[str] = None,
        save: bool = True,
        **kwargs,
    ) -> FileDiff:
        """Create a FileDiff for testing.

        The FileDiff is tied to the given DiffSet. It's populated with
        default data that can be overridden by the caller.

        Args:
            diffset (reviewboard.diffviewer.models.diffset.DiffSet):
                The parent diff set that will own this file.

            source_file (str, optional):
                The source filename.

            dest_file (str, optional):
                The destination filename, which will be the same as
                ``source_file`` unless the file was moved/renamed/copied.

            source_revision (str, optional):
                The source revision.

            dest_detail (str, optional):
                The destination revision or other detail as found in the
                parsed diff. This may be a timestamp or some other value.

            status (str, optional):
                The status of the file. This is the operation performed
                as indicated in the diff.

            diff (bytes, optional):
                The diff contents.

            commit (reviewboard.diffviewer.models.diffcommit.DiffCommit,
                    optional):
                The commit to attach the FileDiff to.

            encoding (str, optional):
                An explicit encoding to set for the file.

            save (bool, optional):
                Whether to automatically save the resulting object.

            **kwargs (dict):
                Additional fields to set on the model.

                Version Added:
                    4.0.5

        Returns:
            reviewboard.diffviewer.models.filediff.FileDiff:
            The resulting FileDiff.
        """
        filediff = FileDiff(
            diffset=diffset,
            source_file=source_file,
            dest_file=dest_file,
            source_revision=source_revision,
            dest_detail=dest_detail,
            status=status,
            diff=diff,
            commit=commit,
            **kwargs)

        if encoding:
            filediff.extra_data['encoding'] = encoding

        if save:
            filediff.save()

        return filediff

    def create_repository(
        self,
        with_local_site: bool = False,
        name: str = 'Test Repo',
        tool_name: str = 'Git',
        path: Optional[str] = None,
        local_site: Optional[LocalSite] = None,
        extra_data: Optional[JSONDict] = None,
        *,
        users: Sequence[User] = [],
        review_groups: Sequence[Group] = [],
        **kwargs,
    ) -> Repository:
        """Create a Repository for testing.

        The Repository may optionally be attached to a
        :py:class:`~reviewboard.site.models.LocalSite`. It's also populated
        with default data that can be overridden by the caller.

        Version Changed:
            5.0.7:
            * Added ``users`` and ``review_groups`` arguments.

        Args:
            with_local_site (bool, optional):
                Whether to create the repository using a Local Site. This
                will choose one based on :py:attr:`local_site_name`.

                If ``local_site`` is provided, this argument is ignored.

            name (str, optional):
                The name of the repository.

            tool_name (str, optional):
                The name of the registered SCM Tool for the repository.

            path (str, optional):
                The path for the repository. If not provided, one will be
                computed.

            local_site (reviewboard.site.models.LocalSite, optional):
                The explicit Local Site to attach.

            extra_data (dict, optional):
                Explicit extra_data to attach to the repository.

            users (list of django.contrib.auth.models.User, optional):
                A list of users to add to the repository.

                Version Added:
                    5.0.7

            review_groups (list of reviewboard.reviews.models.group.Group):
                A list of review groups to add to the repository.

                Version Added:
                    5.0.7

            **kwargs (dict):
                Additional fields to set on the repository.

        Returns:
            reviewboard.scmtools.models.Repository:
            The new repository.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(name=self.local_site_name)
            else:
                local_site = None

        testdata_dir = os.path.join(
            os.path.dirname(reviewboard.scmtools.__file__),
            'testdata')

        if not path:
            if tool_name in ('Git',
                             'Test',
                             'TestToolSupportsPendingChangeSets',
                             'TestToolDiffX'):
                path = os.path.join(testdata_dir, 'git_repo')
            elif tool_name == 'Subversion':
                path = 'file://' + os.path.join(testdata_dir, 'svn_repo')
            elif tool_name == 'Mercurial':
                path = os.path.join(testdata_dir, 'hg_repo.bundle')
            elif tool_name == 'CVS':
                path = os.path.join(testdata_dir, 'cvs_repo')
            elif tool_name == 'Perforce':
                path = 'localhost:1666'
            elif tool_name == 'Bazaar':
                path = 'file://%s' % os.path.join(testdata_dir, 'bzr_repo')
            else:
                raise NotImplementedError

        scmtool = scmtools_registry.get_by_name(tool_name)

        repository = Repository(name=name,
                                local_site=local_site,
                                tool=Tool.objects.get(name=tool_name),
                                scmtool_id=scmtool.scmtool_id,
                                path=path,
                                **kwargs)

        if extra_data is not None:
            repository.extra_data = extra_data

        repository.save()

        if users:
            repository.users.add(*users)

        if review_groups:
            repository.review_groups.add(*review_groups)

        return repository

    def create_review_request(
        self,
        with_local_site: bool = False,
        create_repository: bool = False,
        create_with_history: bool = False,
        publish: bool = False,
        id: Optional[int] = None,
        local_id: Optional[int] = 1001,
        local_site: Optional[LocalSite] = None,
        repository: Optional[Repository] = None,
        time_added: Optional[datetime] = None,
        last_updated: Optional[datetime] = None,
        status: str = ReviewRequest.PENDING_REVIEW,
        submitter: Union[str, User] = 'doc',
        summary: str = 'Test Summary',
        description: str = 'Test Description',
        testing_done: Optional[str] = 'Testing',
        branch: Optional[str] = 'my-branch',
        depends_on: Optional[Sequence[ReviewRequest]] = None,
        target_people: Optional[Sequence[User]] = None,
        target_groups: Optional[Sequence[Group]] = None,
        **kwargs,
    ) -> ReviewRequest:
        """Create a ReviewRequest for testing.

        The :py:class:`~reviewboard.reviews.models.review_request.
        ReviewRequest` may optionally be attached to a
        :py:class:`~reviewboard.site.models.LocalSite`. It's also
        populated with default data that can be overridden by the caller.

        Args:
            with_local_site (bool, optional):
                Whether to create this review request on a default
                :term:`local site`.

                This is ignored if ``local_site`` is provided.

            create_repository (bool, optional):
                Whether to create a new repository in the database for this
                review request.

                This can't be set if ``repository`` is provided.

            create_with_history (bool, optional):
                Whether or not the review request should support multiple
                commits.

            publish (bool, optional):
                Whether to publish the review request after creation.

            id (int, optional):
                An explicit database ID to set for the review request.

            local_id (int, optional):
                The ID specific to the :term:`local site`, if one is used.

            local_site (reviewboard.site.models.LocalSite, optional):
                The LocalSite to associate the review request with.

                If not provided, the LocalSite with the name specified in
                :py:attr:`local_site_name` will be used.

            repository (reviewboard.scmtools.models.Repository, optional):
                An explicit repository to set for the review request.

            time_added (datetime.datetime, optional):
                An explicit creation timestamp to set for the review request.

            last_updated (datetime.datetime, optional):
                An explicit last updated timestamp to set for the review
                request.

            status (str, optional):
                The status of the review request. This must be one of the
                values listed in :py:attr:`~reviewboard.reviews.models.
                review_request.ReviewRequest.STATUSES`.

            submitter (str or django.contrib.auth.models.User, optional):
                The submitter of the review request. This can be a username
                (which will be looked up) or an explicit user.

            summary (str, optional):
                The summary for the review request.

            description (str, optional):
                The description for the review request.

            testing_done (str, optional):
                The Testing Done text for the review request.

            branch (str, optional):
                The branch for the review request.

            depends_on (list of reviewboard.reviews.models.review_request.
                        ReviewRequest, optional):
                A list of review requests to set as dependencies.

            target_people (list of django.contrib.auth.models.User, optional):
                A list of users to set as target reviewers.

            target_groups (list of reviewboard.reviews.models.group.Group,
                           optional):
                A list of review groups to set as target reviewers.

            **kwargs (dict):
                Additional fields to set on the review request.

        Returns:
            reviewboard.reviews.models.review_request.ReviewRequest:
            The resulting review request.

        Raises:
            ValueError:
                An invalid value was provided during initialization.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(name=self.local_site_name)
            else:
                local_site = None

        if not local_site:
            local_id = None

        if create_repository:
            assert not repository

            repository = self.create_repository(local_site=local_site)

        if not isinstance(submitter, User):
            submitter = User.objects.get(username=submitter)

        review_request = ReviewRequest(
            summary=summary,
            description=description,
            branch=branch,
            testing_done=testing_done,
            local_site=local_site,
            local_id=local_id,
            submitter=submitter,
            diffset_history=DiffSetHistory.objects.create(),
            repository=repository,
            status=status,
            **kwargs)

        review_request.created_with_history = create_with_history

        # Set this separately to avoid issues with CounterField updates.
        review_request.id = id  # type: ignore

        review_request.save()

        if depends_on:
            review_request.depends_on.set(depends_on)

        if target_people:
            review_request.target_people.set(target_people)

        if target_groups:
            review_request.target_groups.set(target_groups)

        if publish:
            review_request.publish(review_request.submitter)

        if time_added and last_updated:
            ReviewRequest.objects.filter(pk=review_request.pk).update(
                time_added=time_added,
                last_updated=last_updated)
            review_request.time_added = time_added
            review_request.last_updated = last_updated
        elif time_added:
            ReviewRequest.objects.filter(pk=review_request.pk).update(
                time_added=time_added)
            review_request.time_added = time_added
        elif last_updated:
            ReviewRequest.objects.filter(pk=review_request.pk).update(
                last_updated=last_updated)
            review_request.last_updated = last_updated

        return review_request

    def create_many_review_requests(
        self,
        count: int,
        with_local_site: bool = False,
        create_repository: bool = False,
        create_with_history: bool = True,
        start_id: Optional[int] = None,
        start_local_id: Optional[int] = 1001,
        local_site: Optional[LocalSite] = None,
        repository: Optional[Repository] = None,
        public: bool = False,
        status: str = ReviewRequest.PENDING_REVIEW,
        submitter: Union[str, User] = 'doc',
        summary: str = 'Test Summary %s',
        description: str = 'Test Description %s',
        testing_done: str = 'Testing %s',
        branch: Optional[str] = 'my-branch',
        depends_on: Optional[Sequence[ReviewRequest]] = None,
        target_people: Optional[Sequence[User]] = None,
        target_groups: Optional[Sequence[Group]] = None,
        **kwargs,
    ) -> List[ReviewRequest]:
        """Batch-create multiple ReviewRequests for testing.

        This will execute the minimum number of SQL statements needed to
        add the requested amount of review requests to the database.

        Due to the nature of this method, not every operation supported by
        :py:meth:`create_review_request` is supported here.

        Version Added:
            5.0

        Args:
            count (int):
                The number of review requests to create.

            with_local_site (bool, optional):
                Whether to create the review requests on a default
                :term:`local site`.

                This is ignored if ``local_site`` is provided.

            create_repository (bool, optional):
                Whether to create a new repository in the database, shared
                by all created review requests.

                This can't be set if ``repository`` is provided.

            create_with_history (bool, optional):
                Whether or not the review requests should all support multiple
                commits.

                Note that unlike :py:meth:`create_review_request`, this
                defaults to ``True``.

            start_id (int, optional):
                An explicit database ID to start with for the new review
                requests.

            start_local_id (int, optional):
                The LocalSite-specific ID to use as the start for the new
                review requests.

            local_site (reviewboard.site.models.LocalSite, optional):
                The LocalSite to associate the review requests with.

                If not provided, the LocalSite with the name specified in
                :py:attr:`local_site_name` will be used, if using
                ``with_local_site``.

            repository (reviewboard.scmtools.models.Repository, optional):
                An explicit repository to set for the review request.

            public (bool, optional):
                Whether to mark each review request as public.

            status (str, optional):
                The status of the review requests. This must be one of the
                values listed in :py:attr:`~reviewboard.reviews.models.
                review_request.ReviewRequest.STATUSES`.

            submitter (str or django.contrib.auth.models.User, optional):
                The submitter of the review requests. This can be a username
                (which will be looked up) or an explicit user.

            summary (str, optional):
                The summary for the review request.

                This must contains a ``%s``, which will be replaced with the
                1-based index of the review request.

            description (str, optional):
                The description for the review request.

                This must contains a ``%s``, which will be replaced with the
                1-based index of the review request.

            testing_done (str, optional):
                The Testing Done text for the review request.

                This must contains a ``%s``, which will be replaced with the
                1-based index of the review request.

            branch (str, optional):
                The branch for the review request.

            depends_on (list of reviewboard.reviews.models.review_request.
                        ReviewRequest, optional):
                A list of review requests to set as dependencies for each
                review request.

            target_people (list of django.contrib.auth.models.User, optional):
                A list of users to set as target reviewers for each
                review request.

            target_groups (list of reviewboard.reviews.models.group.Group,
                           optional):
                A list of review groups to set as target reviewers for each
                review request.

            **kwargs (dict):
                Additional fields to set on each review request.

                Note that not all fields can necessarily be set, and some may
                have side effects.

        Returns:
            list of reviewboard.reviews.models.review_request.ReviewRequest:
            The list of resulting review requests.

        Raises:
            ValueError:
                An invalid value was provided during initialization.
        """
        assert count > 0

        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(name=self.local_site_name)
            else:
                local_site = None

        if local_site:
            assert start_local_id is not None
        else:
            start_local_id = None

        if create_repository:
            assert not repository

            repository = \
                self.create_repository(with_local_site=with_local_site)

        if not isinstance(submitter, User):
            submitter = User.objects.get(username=submitter)

        # Create the DiffSetHistories, one per ReviewRequest.
        next_diffset_history_id = DiffSetHistory.objects.count() + 1

        diffset_histories: List[DiffSetHistory] = [
            DiffSetHistory(id=next_diffset_history_id + i)
            for i in range(count)
        ]

        DiffSetHistory.objects.bulk_create(diffset_histories)

        # Create each ReviewRequest.
        if start_id is None:
            start_id = ReviewRequest.objects.count() + 1

        review_requests: List[ReviewRequest] = []
        review_request_ids: List[int] = []

        for i in range(count):
            if start_local_id is None:
                local_id = None
            else:
                local_id = start_local_id + i

            i_display = i + 1

            review_request = ReviewRequest(
                branch=branch,
                description=description % i_display,
                diffset_history=diffset_histories[i],
                local_id=local_id,
                local_site=local_site,
                public=public,
                repository=repository,
                status=status,
                submitter=submitter,
                summary=summary % i_display,
                testing_done=testing_done % i_display,
                **kwargs)
            review_request.created_with_history = create_with_history

            # Set this separately to avoid issues with CounterField updates.
            review_request.pk = start_id + i
            review_request_ids.append(review_request.pk)

            review_requests.append(review_request)

        ReviewRequest.objects.bulk_create(review_requests)

        if depends_on:
            ReviewRequest.depends_on.through.objects.bulk_create(
                ReviewRequest.depends_on.through(
                    from_review_equest=_from_review_request,
                    to_reviewrequest=_to_review_request)
                for _from_review_request in review_requests
                for _to_review_request in depends_on
            )

        if target_people:
            ReviewRequest.target_people.through.objects.bulk_create(
                ReviewRequest.target_people.through(
                    reviewrequest=_review_request,
                    user=_user)
                for _review_request in review_requests
                for _user in target_people
            )

        if target_groups:
            ReviewRequest.target_groups.through.objects.bulk_create(
                ReviewRequest.target_groups.through(
                    review_equest=_review_request,
                    group=_group)
                for _review_request in review_requests
                for _group in target_groups
            )

        if public and status == ReviewRequest.PENDING_REVIEW:
            if target_groups:
                Group.incoming_request_count(target_groups,
                                             increment_by=count)

            if target_people:
                LocalSiteProfile.direct_incoming_request_count.increment(
                    LocalSiteProfile.objects.filter(user__in=target_people,
                                                    local_site=local_site),
                    increment_by=count)

            if target_groups or target_people:
                LocalSiteProfile.total_incoming_request_count.increment(
                    LocalSiteProfile.objects.filter(
                        Q(local_site=local_site) &
                        Q(Q(user__review_groups__in=target_groups or []) |
                          Q(user__in=target_people or []))),
                    increment_by=count)

            try:
                local_site_profile = submitter.get_site_profile(
                    local_site,
                    create_if_missing=False)
            except LocalSiteProfile.DoesNotExist:
                local_site_profile = None
        else:
            local_site_profile = None

        if local_site_profile is not None:
            local_site_profile.increment_total_outgoing_request_count(
                increment_by=count)

            if public:
                local_site_profile.increment_pending_outgoing_request_count(
                    increment_by=count)

        return review_requests

    def create_review_request_draft(
        self,
        review_request: ReviewRequest,
        **kwargs,
    ) -> ReviewRequestDraft:
        """Create a ReviewRequestDraft for testing.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request for the draft.

            **kwargs (dict):
                Additional fields to set on the review request draft.

                Version Added:
                    4.0.5

        Returns:
            reviewboard.reviews.models.review_request_draft.ReviewRequestDraft:
            The newly-created draft.
        """
        return ReviewRequestDraft.create(review_request, **kwargs)

    def create_visit(
        self,
        review_request: ReviewRequest,
        visibility: str,
        user: Union[str, User] = 'doc',
        timestamp: Optional[datetime] = None,
        **kwargs,
    ) -> ReviewRequestVisit:
        """Create a ReviewRequestVisit for testing.

        The ReviewRequestVisit is tied to the given ReviewRequest and User.
        It's populated with default data that can be overridden by the caller.

        The provided user may either be a username or a User object.

        Version Changed:
            5.0.7:
            * ``timestamp`` and ``user`` are now processed and set correctly.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request that was visited.

            visibility (str):
                The visibility state for the visit.

            user (str or django.contrib.auth.models.User):
                The user that visited the review request.

            timestamp (datetime.datetime, optional):
                The timestamp of the visit.

            **kwargs (dict):
                Additional fields to set on the visit.

        Returns:
            reviewboard.accounts.models.ReviewRequestVisit:
            The newly-created visit object.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        if timestamp is not None:
            # Avoid passing in a None directly, and use the model's handling.
            kwargs['timestamp'] = timestamp

        return ReviewRequestVisit.objects.create(
            review_request=review_request,
            visibility=visibility,
            user=user,
            **kwargs)

    def create_review(
        self,
        review_request: ReviewRequest,
        user: Union[str, User] = 'dopey',
        body_top: Optional[str] = 'Test Body Top',
        body_bottom: Optional[str] = 'Test Body Bottom',
        ship_it: bool = False,
        publish: bool = False,
        timestamp: Optional[datetime] = None,
        **kwargs,
    ) -> Review:
        """Create a Review for testing.

        The Review is tied to the given ReviewRequest. It's populated with
        default data that can be overridden by the caller.

        The provided user may either be a username or a User object.

        If publish is True, Review.publish() will be called.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request the review is filed against.

            user (str or django.contrib.auth.models.User, optional):
                The username or User object owning the review.

            body_top (str, optional):
                The text for the ``body_top`` field.

            body_bottom (str, optional):
                The text for the ``body_bottom`` field.

            ship_it (bool, optional):
                The Ship It state for the review.

            publish (bool, optional):
                Whether to publish the review immediately after creation.

            timestamp (datetime.datetime, optional):
                The timestamp for the review.

            **kwargs (dict):
                Additional attributes to set in the review.

        Returns:
            reviewboard.reviews.models.review.Review:
            The resulting review.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        review = Review.objects.create(
            review_request=review_request,
            user=user,
            body_top=body_top,
            body_bottom=body_bottom,
            ship_it=ship_it,
            **kwargs)

        if publish:
            review.publish()

        if timestamp:
            Review.objects.filter(pk=review.pk).update(timestamp=timestamp)
            review.timestamp = timestamp

        return review

    def create_review_group(
        self,
        name: str = 'test-group',
        with_local_site: bool = False,
        local_site: Optional[LocalSite] = None,
        visible: bool = True,
        invite_only: bool = False,
        is_default_group: bool = False,
        *,
        users: Sequence[User] = [],
        **kwargs,
    ) -> Group:
        """Create a review group for testing.

        The group may optionally be attached to a LocalSite. It's also
        populated with default data that can be overridden by the caller.

        Version Changed:
            5.0.7:
            * Added ``users`` arguments.

        Args:
            name (str, optional):
                The name of the review group.

            with_local_site (bool, optional):
                Whether to create the repository using a Local Site. This
                will choose one based on :py:attr:`local_site_name`.

                If ``local_site`` is provided, this argument is ignored.

            local_site (reviewboard.site.models.LocalSite, optional):
                The explicit Local Site to attach.

            visible (bool, optional):
                Whether the review group should be visible.

            invite_only (bool, optional):
                Whether the review group should be invite-only.

            is_default_group (bool, optional):
                Whether this review group is a default for new users.

            users (list of django.contrib.auth.models.User, optional):
                A list of users to add to the review group.

                Version Added:
                    5.0.7
        """
        if not local_site and with_local_site:
            local_site = self.get_local_site(name=self.local_site_name)

        group = Group.objects.create(
            name=name,
            local_site=local_site,
            visible=visible,
            invite_only=invite_only,
            is_default_group=is_default_group,
            **kwargs)

        if users:
            group.users.add(*users)

        return group

    def create_reply(
        self,
        review: Review,
        user: Union[str, User] = 'grumpy',
        body_top: Optional[str] = 'Test Body Top',
        timestamp: Optional[datetime] = None,
        publish: bool = False,
        **kwargs,
    ) -> Review:
        """Create a review reply for testing.

        The reply is tied to the given Review. It's populated with default
        data that can be overridden by the caller.

        To reply to a ``body_top`` or ``body_bottom`` field, pass either
        ``body_top_reply_to=`` or ``body_bottom_reply_to=`` to this method.
        This will be passed to the review's constructor.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review being replied to.

            user (django.contrib.auth.models.User or str, optional):
                Either the user model or the username of the user who is
                replying to the review.

            body_top (str, optional):
                The body top text.

            timestamp (datetime.datetime, optional):
                The timestamp of the review.

            publish (bool, optional):
                Whether the review should be published. By default it's in
                draft form.

            **kwargs (dict):
                Additional arguments to pass to the
                :py:class:`~reviewboard.reviews.models.review.Review`
                constructor.

                Version Added:
                    4.0.5

        Returns:
            reviewboard.reviews.models.review.Review:
            The resulting review.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        reply = Review.objects.create(
            review_request=review.review_request,
            user=user,
            body_top=body_top,
            base_reply_to=review,
            **kwargs)

        if publish:
            reply.publish()

        if timestamp:
            Review.objects.filter(pk=reply.pk).update(timestamp=timestamp)
            reply.timestamp = timestamp

        return reply

    def create_screenshot(
        self,
        review_request: ReviewRequest,
        caption: str = 'My caption',
        draft: bool = False,
        active: bool = True,
        **kwargs,
    ) -> Screenshot:
        """Create a Screenshot for testing.

        The screenshot is tied to the given
        :py:class:`~reviewboard.reviews.models.review_request.ReviewRequest`.
        It's populated with default data that can be overridden by the caller.

        Args:
            review_request (reviewboard.reviews.models.review_request.
                            ReviewRequest):
                The review request that ultimately owns the screenshot.

            caption (str, optional):
                The caption to use for the screenshot.

            draft (bool or
                   reviewboard.reviews.models.review_request_draft.
                   ReviewRequestDraft):
                A draft to associate the screenshot with. This can also be
                a boolean, for legacy reasons, which will attempt to look up
                or create a draft for the review request.

            active (bool):
                Whether this screenshot is considered active (not deleted).

            **kwargs (dict):
                Additional fields to set on the screenshot.

        Returns:
            reviewboard.reviews.models.screenshot.Screenshot:
            The resulting screenshot.
        """
        screenshot = Screenshot(caption=caption, **kwargs)
        filename = os.path.join(_static_root, 'rb', 'images', 'logo.png')

        with open(filename, 'rb') as f:
            screenshot.image.save(os.path.basename(filename), File(f),
                                  save=True)

        if draft:
            if isinstance(draft, ReviewRequestDraft):
                review_request_draft = draft
            else:
                review_request_draft = \
                    self.create_review_request_draft(review_request)

            if active:
                screenshots = review_request_draft.screenshots
            else:
                screenshots = review_request_draft.inactive_screenshots
        else:
            if active:
                screenshots = review_request.screenshots
            else:
                screenshots = review_request.inactive_screenshots

        screenshots.add(screenshot)

        return screenshot

    def create_screenshot_comment(
        self,
        review: Review,
        screenshot: Screenshot,
        text: str = 'My comment',
        x: int = 1,
        y: int = 1,
        w: int = 5,
        h: int = 5,
        issue_opened: bool = False,
        issue_status: Optional[str] = None,
        extra_fields: Optional[JSONDict] = None,
        reply_to: Optional[ScreenshotComment] = None,
        timestamp: Optional[datetime] = None,
        **kwargs,
    ) -> ScreenshotComment:
        """Create a ScreenshotComment for testing.

        The comment is tied to the given Review and Screenshot. It's
        It's populated with default data that can be overridden by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review associated with the comment.

            screenshot (reviewboard.reviews.models.screenshot.Screenshot):
                The screenshot associated with the comment.

            text (str):
                The text for the comment.

            x (int, optional):
                The X location for the comment on the screenshot.

            y (int, optional):
                The Y location for the comment on the screenshot.

            w (int, optional):
                The width for the comment on the screenshot.

            h (int, optional):
                The height for the comment on the screenshot.

            issue_opened (bool, optional):
                Whether an issue is to be opened for the comment.

            issue_status (str, optional):
                The issue status to set, if an issue is opened. Defaults to
                being an open issue.

            extra_fields (dict, optional):
                Extra data to set on the comment.

            reply_to (reviewboard.reviews.models.screenshot_comment.
                      ScreenshotComment, optional):
                The comment this comment replies to.

            timestamp (datetime.datetime, optional):
                The timestamp for the comment.

                Version Added:
                    5.0

            **kwargs (dict):
                Additional model attributes to set on the comment.

        Returns:
            reviewboard.reviews.models.screenshot_comment.ScreenshotComment:
            The resulting comment.
        """
        if issue_opened and not issue_status:
            issue_status = ScreenshotComment.OPEN

        comment = ScreenshotComment(
            screenshot=screenshot,
            text=text,
            x=x,
            y=y,
            w=w,
            h=h,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to,
            **kwargs)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.screenshot_comments.add(comment)

        if timestamp:
            queryset = ScreenshotComment.objects.filter(pk=comment.pk)
            queryset.update(timestamp=timestamp)
            comment.timestamp = timestamp

        return comment

    def create_file_attachment_base(
        self,
        caption: str = 'My Caption',
        orig_filename: str = 'logo.png',
        mimetype: str = 'image/png',
        uuid: Optional[str] = None,
        has_file: bool = True,
        file_content: Optional[bytes] = None,
        user: Optional[User] = None,
        with_local_site: bool = False,
        local_site_name: Optional[str] = None,
        local_site: Optional[LocalSite] = None,
        **kwargs,
    ) -> FileAttachment:
        """Base helper to create a FileAttachment object.

        When creating a
        :py:class:`reviewboard.attachments.models.FileAttachment` that will be
        associated to a review request, a user and local_site should not be
        specified.

        This is not meant to be called directly by tests. Callers should
        generallly use one of:

        * :py:meth:`create_file_attachment`
        * :py:meth:`create_user_file_attachment`

        Args:
            caption (str, optional):
                The caption for the file attachment.

            orig_filename (str, optional):
                The original name of the file to set in the model.

            mimetype (str, optional):
                The mimetype of the file attachment.

            uuid (str, optional):
                The UUID used to prefix the filename and reference the
                file attachment.

            has_file (bool, optional):
                ``True`` if an actual file object should be included in the
                model.

                This will set the file content based on ``file_content``, if
                one is provided. If not provided, the Review Board logo is used
                as the file content.

            file_content (bytes, optional):
                The file content. This is only set if passing
                ``has_file=True``.

            user (django.contrib.auth.models.User, optional):
                The user who owns the file attachment.

            with_local_site (bool, optional):
                ``True`` if the file attachment should be associated with a
                local site. If this is set, one of ``local_site_name`` or
                ``local_site`` should be provided as well.

            local_site_name (str, optional):
                The name of the local site to associate this attachment with.

            local_site (reviewboard.site.models.LocalSite, optional):
                The local site to associate this attachment with.

            kwargs (dict):
                Additional keyword arguments to pass into the FileAttachment
                constructor.

        Returns:
            reviewboard.attachments.models.FileAttachment:
            The new file attachment instance.
        """
        if with_local_site:
            local_site = self.get_local_site(name=local_site_name)

        if not uuid:
            uuid = str(uuid4())

        attachment_revision = kwargs.pop('attachment_revision', 1)
        draft_caption = kwargs.pop('draft_caption', caption)
        filename = kwargs.get('filename', f'{uuid}-{orig_filename}')

        file_attachment = FileAttachment(
            attachment_revision=attachment_revision,
            caption=caption,
            draft_caption=draft_caption,
            mimetype=mimetype,
            user=user,
            uuid=uuid,
            local_site=local_site,
            orig_filename=orig_filename,
            **kwargs)

        if has_file:
            if file_content is None:
                logo_path = os.path.join(_static_root, 'rb', 'images',
                                         'logo.png')

                with open(logo_path, 'rb') as fp:
                    file_content = fp.read()

            assert isinstance(file_content, bytes), (
                'file_content must be passed as bytes, not %s'
                % type(file_content))

            file_attachment.file.save(filename,
                                      ContentFile(file_content),
                                      save=True)

        file_attachment.save()

        return file_attachment

    def create_general_comment(
        self,
        review: Review,
        text: str = 'My comment',
        issue_opened: bool = False,
        issue_status: Optional[str] = None,
        extra_fields: Optional[JSONDict] = None,
        reply_to: Optional[GeneralComment] = None,
        timestamp: Optional[datetime] = None,
        **kwargs,
    ) -> GeneralComment:
        """Create a GeneralComment for testing.

        The comment is tied to the given Review. It is populated with
        default data that can be overridden by the caller.

        Args:
            review (reviewboard.reviews.models.review.Review):
                The review associated with the comment.

            text (str):
                The text for the comment.

            issue_opened (bool, optional):
                Whether an issue is to be opened for the comment.

            issue_status (str, optional):
                The issue status to set, if an issue is opened. Defaults to
                being an open issue.

            extra_fields (dict, optional):
                Extra data to set on the comment.

            reply_to (reviewboard.reviews.models.general_comment.
                      GeneralComment, optional):
                The comment this comment replies to.

            timestamp (datetime.datetime, optional):
                The timestamp for the comment.

                Version Added:
                    5.0

            **kwargs (dict):
                Additional model attributes to set on the comment.

        Returns:
            reviewboard.reviews.models.general_comment.GeneralComment:
            The resulting comment.
        """
        if issue_opened and not issue_status:
            issue_status = GeneralComment.OPEN

        comment = GeneralComment(
            text=text,
            issue_opened=issue_opened,
            issue_status=issue_status,
            reply_to=reply_to,
            **kwargs)

        if extra_fields:
            comment.extra_data = extra_fields

        comment.save()
        review.general_comments.add(comment)

        if timestamp:
            queryset = GeneralComment.objects.filter(pk=comment.pk)
            queryset.update(timestamp=timestamp)
            comment.timestamp = timestamp

        return comment

    def create_status_update(
        self,
        review_request: ReviewRequest,
        user: Union[str, User] = 'dopey',
        service_id: str = 'service',
        summary: str = 'Status Update',
        state: str = StatusUpdate.PENDING,
        review: Optional[Review] = None,
        change_description: Optional[ChangeDescription] = None,
        timestamp: Optional[datetime] = None,
        **kwargs,
    ) -> StatusUpdate:
        """Create a status update for testing.

        It is populated with default data that can be overridden by the caller.

        Args:
            review_request (reviewboard.reviews.models.ReviewRequest):
                The review request to associate with the new status update.

            user (django.contrib.auth.models.User or str):
                Either the user model or the username of the user who should
                own the status update.

            service_id (str):
                The ID to fill in for the new model.

            summary (str):
                The summary to fill in for the new model.

            state (str):
                The state for the new model. This must be one of the valid
                choices for the state field.

            review (reviewboard.reviews.models.review.Review, optional):
                The review associated with this status update.

            change_description (reviewboard.changedescs.models.
                                ChangeDescription, optional):
                The change description for this status update.

            timestamp (datetime.datetime):
                The timestamp for the status update.

            **kwargs (dict):
                Additional fields to set on the status update model.

                Version Added:
                    4.0.5

        Returns:
            reviewboard.reviews.models.StatusUpdate:
            The new status update.
        """
        if not isinstance(user, User):
            user = User.objects.get(username=user)

        status_update = StatusUpdate.objects.create(
            review_request=review_request,
            change_description=change_description,
            service_id=service_id,
            summary=summary,
            state=state,
            review=review,
            user=user,
            **kwargs)

        if timestamp:
            StatusUpdate.objects.filter(pk=status_update.pk).update(
                timestamp=timestamp)
            status_update.timestamp = timestamp

        return status_update

    def create_webhook(
        self,
        enabled: bool = False,
        events: str = WebHookTarget.ALL_EVENTS,
        url: str = 'http://example.com',
        encoding: str = WebHookTarget.ENCODING_JSON,
        use_custom_content: bool = False,
        custom_content: str = '',
        secret: str = '',
        apply_to: str = WebHookTarget.APPLY_TO_ALL,
        repositories: Optional[Sequence[Repository]] = None,
        with_local_site: bool = False,
        local_site: Optional[LocalSite] = None,
        extra_fields: Optional[JSONDict] = None,
        **kwargs,
    ) -> WebHookTarget:
        """Create a webhook for testing.

        It is populated with default data that can be overridden by the caller.

        Args:
            enabled (bool):
                Whether or not the webhook is enabled when it is created.

            events (str):
                A comma-separated list of events that the webhook will trigger
                on.

            url (str):
                The URL that requests will be made against.

            encoding (str):
                The encoding of the payload to send.

            use_custom_content (bool):
                Determines if custom content will be sent for the payload (if
                ``True``) or if it will be auto-generated (if ``False``).

            custom_content (str):
                The custom content to send when ``use_custom_content`` is
                ``True``.

            secret (str):
                An HMAC secret to sign the payload with.

            apply_to (str):
                The types of repositories the webhook will apply to.

            repositories (list):
                A list of repositories that the webhook will be limited to if
                ``apply_to`` is ``WebHookTarget.APPLY_TO_SELECTED_REPOS``.

            with_local_site (bool):
                Determines if this should be created with a local site.

            local_site (reviewboard.site.models.LocalSite):
                An optional local site. If ``with_local_site`` is ``True`` and
                this argument is ``None``, the local site will be looked up.

            extra_fields (dict):
                Extra data to be imported into the webhook.

            **kwargs (dict):
                Additional keyword arguments to pass into the WebHookTarget
                constructor.

                Version Added:
                    4.0.5

        Returns:
            WebHookTarget:
            A webhook constructed with the given arguments.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(name=self.local_site_name)
            else:
                local_site = None

        webhook = WebHookTarget.objects.create(
            enabled=enabled,
            events=events.split(','),
            url=url,
            encoding=encoding,
            use_custom_content=use_custom_content,
            custom_content=custom_content,
            secret=secret,
            apply_to=apply_to,
            local_site=local_site,
            **kwargs)

        if repositories:
            webhook.repositories.set(repositories)

        if extra_fields:
            webhook.extra_data = extra_fields
            webhook.save(update_fields=['extra_data'])

        return webhook

    def create_oauth_application(
        self,
        user: User,
        local_site: Optional[LocalSite] = None,
        with_local_site: bool = False,
        redirect_uris: str = 'http://example.com',
        authorization_grant_type: str = Application.GRANT_CLIENT_CREDENTIALS,
        client_type: str = Application.CLIENT_PUBLIC,
        **kwargs,
    ) -> Application:
        """Create an OAuth application.

        Args:
            user (django.contrib.auth.models.User):
                The user whom is to own the application.

            local_site (reviewboard.site.models.LocalSite, optional):
                The LocalSite for the application to be associated with, if
                any.

            redirect_uris (str, optional):
                A whitespace-separated list of allowable redirect URIs.

            authorization_grant_type (str, optional):
                The grant type for the application.

            client_type (str, optional):
                The application client type.

            **kwargs (dict):
                Additional keyword arguments to pass to the
                :py:class:`~reviewboard.oauth.models.Application` initializer.

        Returns:
            reviewboard.oauth.models.Application:
            The created application.
        """
        if not local_site:
            if with_local_site:
                local_site = self.get_local_site(self.local_site_name)
            else:
                local_site = None

        return Application.objects.create(
            user=user,
            local_site=local_site,
            authorization_grant_type=authorization_grant_type,
            redirect_uris=redirect_uris,
            client_type=client_type,
            extra_data='{}',
            **kwargs)

    def create_oauth_token(
        self,
        application: Application,
        user: User,
        scope: str = '',
        expires: Optional[timedelta] = None,
        **kwargs,
    ) -> AccessToken:
        """Create an OAuth2 access token for testing.

        Args:
            application (reviewboard.oauth.models.Application):
                The application the token should be associated with.

            user (django.contrib.auth.models.User):
                The user who should own the token.

            scope (str, optional):
                The scopes of the token. This argument defaults to the empty
                scope.

            expires (datetime.timedelta, optional):
                How far into the future the token expires. If not provided,
                this argument defaults to one hour.

            **kwargs (dict):
                Additional keyword arguments to pass into the AccessToken
                constructor.

                Version Added:
                    4.0.5

        Returns:
            oauth2_provider.models.AccessToken:
            The created access token.
        """
        if expires is None:
            expires = timedelta(hours=1)

        return AccessToken.objects.create(
            application=application,
            token=generate_token(),
            expires=now() + expires,
            scope=scope,
            user=user,
            **kwargs
        )

    def create_certificate(
        self,
        *,
        hostname: str = 'example.com',
        port: int = 443,
        subject: Unsettable[str] = 'Test Subject',
        issuer: Unsettable[str] = 'Test Issuer',
        valid_from: Unsettable[Optional[datetime]] = None,
        valid_through: Unsettable[Optional[datetime]] = None,
        fingerprints: Unsettable[Optional[CertificateFingerprints]] = None,
        cert_data: Optional[bytes] = None,
        key_data: Optional[bytes] = None,
        **kwargs,
    ) -> Certificate:
        """Return a Certificate for testing.

        This will be pre-populated with default signature data and values,
        if not otherwise specified.

        If ``cert_data`` is provided, then most arguments will be ignored
        in favor of the values in the certificate.

        Version Added:
            6.0

        Args:
            hostname (str, optional):
                The hostname that would serve the certificate.

            port (int, optional):
                The port on the host that would serve the certificate.

            subject (str, optional):
                The subject (usually the hostname) of the certificate.

                This can be :py:data:`~djblets.util.symbols.UNSET` to force
                loading from a ``cert_data`` (if provided).

            issuer (str, optional):
                The issuer of the certificate.

                This can be :py:data:`~djblets.util.symbols.UNSET` to force
                loading from a ``cert_data`` (if provided).

            valid_from (datetime, optional):
                The first date/time in which the certificate is valid.

                This must have a timezone associated with it.

                If not provided or ``None``, a default timestamp of
                2023-07-14 7:50:30 UTC will be used.

                This can be :py:data:`~djblets.util.symbols.UNSET` to force
                loading from a ``cert_data`` (if provided).

            valid_through (datetime, optional):
                The last date/time in which the certificate is valid.

                This must have a timezone associated with it.

                If not provided or ``None``, a default timestamp of
                3023-07-14 7:50:30 UTC will be used.

                This can be :py:data:`~djblets.util.symbols.UNSET` to force
                loading from a ``cert_data`` (if provided).

            fingerprints (CertificateFingerprints, optional):
                Fingerprints to set for the certificate.

                If not provided or ``None``, default fingerprints will be
                created using :py:meth:`create_certificate_fingerprints`.

                This can be :py:data:`~djblets.util.symbols.UNSET` to force
                loading from a ``cert_data`` (if provided).

            cert_data (bytes, optional):
                PEM-formatted certificate data to load.

                If set, ``subject``, ``issuer``, ``valid_from``,
                ``valid_through``, and ``fingerprints`` arguments will be
                ignored.

            key_data (bytes, optional):
                PEM-formatted private key data to load.

            **kwargs (dict):
                Additional keyword arguments supported by the
                :py:class:`~reviewboard.certs.cert.Certificate` constructor.

        Returns:
            reviewboard.certs.cert.Certificate:
            The new certificate instance.
        """
        if cert_data is not None:
            return Certificate(hostname=hostname,
                               port=port,
                               cert_data=cert_data,
                               key_data=key_data,
                               **kwargs)
        else:
            if fingerprints is None:
                fingerprints = self.create_certificate_fingerprints()

            if valid_from is None:
                valid_from = datetime(2023, 7, 14, 7, 50, 30,
                                      tzinfo=timezone.utc)

            if valid_through is None:
                valid_through = datetime(3023, 7, 14, 7, 50, 30,
                                         tzinfo=timezone.utc)

            return Certificate(hostname=hostname,
                               port=port,
                               subject=subject,
                               issuer=issuer,
                               fingerprints=fingerprints,
                               valid_from=valid_from,
                               valid_through=valid_through,
                               key_data=key_data,
                               **kwargs)

    def create_certificate_bundle(
        self,
        *,
        bundle_data: Optional[bytes] = None,
        **kwargs,
    ) -> CertificateBundle:
        """Return a CertificateBundle for testing.

        This will be pre-populated with default data, unless otherwise
        specified.

        Version Added:
            6.0

        Args:
            bundle_data (bytes, optional):
                Explicit bundle data to load.

                If a value is not specified or is ``None``, a sample bundle
                will be used.

            **kwargs (dict, optional):
                Additional keyword arguments supported by the
                :py:class:`~reviewboard.certs.cert.CertificateBundle`
                constructor.

        Returns:
            reviewboard.certs.cert.CertificateFingerprints:
            The new fingerprints instance.
        """
        from reviewboard.certs.tests.testcases import TEST_CERT_BUNDLE_PEM

        if bundle_data is None:
            bundle_data = TEST_CERT_BUNDLE_PEM

        return CertificateBundle(bundle_data=bundle_data,
                                 **kwargs)

    def create_certificate_fingerprints(
        self,
        *,
        sha1: Unsettable[Optional[str]] = UNSET,
        sha256: Unsettable[Optional[str]] = UNSET,
        **kwargs,
    ) -> CertificateFingerprints:
        """Return a CertificateFingerprints for testing.

        This will be pre-populated with default SHA1 and SHA256 signatures,
        if custom signatures are not supplied.

        Version Added:
            6.0

        Args:
            sha1 (str, optional):
                An explicit SHA1 fingerprint to set, or ``None`` to unset.

                If a value is not specified,
                :py:data:`reviewboard.certs.tests.testcases.TEST_SHA1` will be
                set.

            sha256 (str, optional):
                An explicit SHA256 fingerprint to set, or ``None`` to unset.

                If a value is not specified,
                :py:data:`reviewboard.certs.tests.testcases.TEST_SHA256` will
                be set.

            **kwargs (dict, optional):
                Additional keyword arguments supported by the
                :py:class:`~reviewboard.certs.cert.CertificateFingerprints`
                constructor.

        Returns:
            reviewboard.certs.cert.CertificateFingerprints:
            The new fingerprints instance.
        """
        from reviewboard.certs.tests.testcases import TEST_SHA1, TEST_SHA256

        if sha1 is UNSET:
            sha1 = TEST_SHA1

        if sha256 is UNSET:
            sha256 = TEST_SHA256

        return CertificateFingerprints(sha1=sha1,
                                       sha256=sha256,
                                       **kwargs)

    @contextmanager
    def siteconfig_settings(
        self,
        settings: JSONDict,
        reload_settings: bool = True,
    ) -> Iterator[None]:
        """Temporarily sets siteconfig settings for a test.

        Args:
            settings (dict):
                The new siteconfig settings to set.

            reload_settings (bool, optional):
                Whether to reload and recompute all settings, applying them
                to Django and other objects.

        Context:
            The current site configuration will contain the new settings for
            this test.
        """
        try:
            with super(TestCase, self).siteconfig_settings(settings):
                if reload_settings:
                    load_site_config()

                yield
        finally:
            if reload_settings:
                load_site_config()


class BaseFileDiffAncestorTests(kgb.SpyAgency, TestCase):
    """A base test case that creates a FileDiff history."""

    fixtures = ['test_scmtools', 'test_users']

    _COMMITS = [
        {
            'parent': (
                b'diff --git a/bar b/bar\n'
                b'index e69de29..5716ca5 100644\n'
                b'--- a/bar\n'
                b'+++ b/bar\n'
                b'@@ -0,0 +1 @@\n'
                b'+bar\n'
            ),
            'diff': (
                b'diff --git a/foo b/foo\n'
                b'new file mode 100644\n'
                b'index 0000000..e69de29\n'

                b'diff --git a/bar b/bar\n'
                b'index 5716ca5..8e739cc 100644\n'
                b'--- a/bar\n'
                b'+++ b/bar\n'
                b'@@ -1 +1 @@\n'
                b'-bar\n'
                b'+bar bar bar\n'
            ),
        },
        {
            'parent': (
                b'diff --git a/baz b/baz\n'
                b'new file mode 100644\n'
                b'index 0000000..7601807\n'
                b'--- /dev/null\n'
                b'+++ b/baz\n'
                b'@@ -0,0 +1 @@\n'
                b'+baz\n'
            ),
            'diff': (
                b'diff --git a/foo b/foo\n'
                b'index e69de29..257cc56 100644\n'
                b'--- a/foo\n'
                b'+++ b/foo\n'
                b'@@ -0,0 +1 @@\n'
                b'+foo\n'

                b'diff --git a/bar b/bar\n'
                b'deleted file mode 100644\n'
                b'index 8e739cc..0000000\n'
                b'--- a/bar\n'
                b'+++ /dev/null\n'
                b'@@ -1 +0,0 @@\n'
                b'-bar -bar -bar\n'

                b'diff --git a/baz b/baz\n'
                b'index 7601807..280beb2 100644\n'
                b'--- a/baz\n'
                b'+++ b/baz\n'
                b'@@ -1 +1 @@\n'
                b'-baz\n'
                b'+baz baz baz\n'
            ),
        },
        {
            'parent': (
                b'diff --git a/corge b/corge\n'
                b'new file mode 100644\n'
                b'index 0000000..e69de29\n'
            ),
            'diff': (
                b'diff --git a/foo b/qux\n'
                b'index 257cc56..03b37a0 100644\n'
                b'--- a/foo\n'
                b'+++ b/qux\n'
                b'@@ -1 +1 @@\n'
                b'-foo\n'
                b'+foo bar baz qux\n'

                b'diff --git a/bar b/bar\n'
                b'new file mode 100644\n'
                b'index 0000000..5716ca5\n'
                b'--- /dev/null\n'
                b'+++ b/bar\n'
                b'@@ -0,0 +1 @@\n'
                b'+bar\n'

                b'diff --git a/corge b/corge\n'
                b'index e69de29..f248ba3 100644\n'
                b'--- a/corge\n'
                b'+++ b/corge\n'
                b'@@ -0,0 +1 @@\n'
                b'+corge\n'
            ),
        },
        {
            'parent': None,
            'diff': (
                b'diff --git a/bar b/quux\n'
                b'index 5716ca5..e69de29 100644\n'
                b'--- a/bar\n'
                b'+++ b/quux\n'
                b'@@ -1 +0,0 @@\n'
                b'-bar\n'
            ),
        },
    ]

    _CUMULATIVE_DIFF = {
        'parent': b''.join(
            parent_diff
            for parent_diff in (
                entry['parent']
                for entry in _COMMITS
            )
            if parent_diff is not None
        ),
        'diff': (
            b'diff --git a/qux b/qux\n'
            b'new file mode 100644\n'
            b'index 000000..03b37a0\n'
            b'--- /dev/null\n'
            b'+++ /b/qux\n'
            b'@@ -0,0 +1 @@\n'
            b'foo bar baz qux\n'

            b'diff --git a/bar b/quux\n'
            b'index 5716ca5..e69de29 100644\n'
            b'--- a/bar\n'
            b'+++ b/quux\n'
            b'@@ -1 +0,0 @@\n'
            b'-bar\n'

            b'diff --git a/baz b/baz\n'
            b'index 7601807..280beb2 100644\n'
            b'--- a/baz\n'
            b'+++ b/baz\n'
            b'@@ -1 +1 @@\n'
            b'-baz\n'
            b'+baz baz baz\n'

            b'diff --git a/corge b/corge\n'
            b'index e69de29..f248ba3 100644\n'
            b'--- a/corge\n'
            b'+++ b/corge\n'
            b'@@ -0,0 +1 @@\n'
            b'+corge\n'
        ),
    }

    _FILES = {
        ('bar', 'e69de29'): b'',
    }

    # A mapping of filediff details to the details of its ancestors in
    # (compliment, minimal) form.
    _HISTORY = {
        (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'): ([], []),
        (1, 'bar', 'e69de29', 'bar', '8e739cc'): ([], []),
        (2, 'foo', 'e69de29', 'foo', '257cc56'): (
            [],
            [
                (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'),
            ],
        ),
        (2, 'bar', '8e739cc', 'bar', '0000000'): (
            [],
            [
                (1, 'bar', 'e69de29', 'bar', '8e739cc'),
            ],
        ),
        (2, 'baz', 'PRE-CREATION', 'baz', '280beb2'): ([], []),
        (3, 'foo', '257cc56', 'qux', '03b37a0'): (
            [],
            [
                (1, 'foo', 'PRE-CREATION', 'foo', 'e69de29'),
                (2, 'foo', 'e69de29', 'foo', '257cc56'),
            ],
        ),
        (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'): (
            [
                (1, 'bar', 'e69de29', 'bar', '8e739cc'),
                (2, 'bar', '8e739cc', 'bar', '0000000'),
            ],
            [],
        ),
        (3, 'corge', 'PRE-CREATION', 'corge', 'f248ba3'): ([], []),
        (4, 'bar', '5716ca5', 'quux', 'e69de29'): (
            [
                (1, 'bar', 'e69de29', 'bar', '8e739cc'),
                (2, 'bar', '8e739cc', 'bar', '0000000'),
            ],
            [
                (3, 'bar', 'PRE-CREATION', 'bar', '5716ca5'),
            ],
        ),
    }

    def set_up_filediffs(self) -> None:
        """Create a set of commits with history."""
        @self.spy_for(Repository.get_file, owner=Repository)
        def get_file(
            repo: Repository,
            path: str,
            revision: str,
            *args,
            base_commit_id: Optional[str] = None,
            context: Optional[FileLookupContext] = None,
            **kwargs,
        ) -> bytes:
            if repo == self.repository:
                try:
                    return self._FILES[(path, revision)]
                except KeyError:
                    pass

            raise FileNotFoundError(path=path,
                                    revision=revision,
                                    base_commit_id=base_commit_id,
                                    context=context)

        self.repository = self.create_repository(tool_name='Git')
        self.review_request = self.create_review_request(
            repository=self.repository,
            publish=True)

        self.spy_on(Repository.get_file_exists,
                    owner=Repository,
                    op=kgb.SpyOpReturn(True))

        self.diffset = self.create_diffset(review_request=self.review_request)
        self.diff_commits = []

        for i, diff in enumerate(self._COMMITS, 1):
            commit_id = 'r%d' % i
            parent_id = 'r%d' % (i - 1)

            self.diff_commits.append(self.create_diffcommit(
                diffset=self.diffset,
                repository=self.repository,
                commit_id=commit_id,
                parent_id=parent_id,
                diff_contents=diff['diff'],
                parent_diff_contents=diff['parent']))

        self.filediffs = list(FileDiff.objects.all())
        self.diffset.finalize_commit_series(
            cumulative_diff=self._CUMULATIVE_DIFF['diff'],
            parent_diff=self._CUMULATIVE_DIFF['parent'],
            validation_info=None,
            validate=False,
            save=True)

        # This was only necessary so that we could side step diff validation
        # during creation.
        Repository.get_file_exists.unspy()

    def get_filediffs_by_details(self):
        """Return a mapping of FileDiff details to the FileDiffs.

        Returns:
            dict:
            A mapping of FileDiff details to FileDiffs.
        """
        return {
            (
                filediff.commit_id,
                filediff.source_file,
                filediff.source_revision,
                filediff.dest_file,
                filediff.dest_detail,
            ): filediff
            for filediff in self.filediffs
        }
