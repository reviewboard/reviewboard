import os

import kgb
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db.models import Q
from djblets.testing.decorators import add_fixtures

from reviewboard.hostingsvcs.errors import MissingHostingServiceError
from reviewboard.hostingsvcs.github import GitHub
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.scmtools.core import FileLookupContext
from reviewboard.scmtools.git import GitTool
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.signals import (checked_file_exists,
                                          checking_file_exists,
                                          fetched_file, fetching_file)
from reviewboard.testing.testcase import TestCase


class RepositoryTests(kgb.SpyAgency, TestCase):
    """Unit tests for Repository operations."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(RepositoryTests, self).setUp()

        self.local_repo_path = os.path.join(os.path.dirname(__file__),
                                            '..', 'testdata', 'git_repo')
        self.repository = self.create_repository(
            name='Git test repo',
            path=self.local_repo_path,
            tool_name='Git')

    def test_archive(self):
        """Testing Repository.archive"""
        repository1 = self.repository

        repository1.archive()
        self.assertTrue(repository1.name.startswith('ar:Git test repo:'))
        self.assertTrue(repository1.archived)
        self.assertFalse(repository1.public)
        self.assertIsNotNone(repository1.archived_timestamp)

        repository2 = Repository.objects.get(pk=repository1.pk)
        self.assertEqual(repository2.name,
                         repository1.name)
        self.assertEqual(repository2.archived,
                         repository1.archived)
        self.assertEqual(repository2.public,
                         repository1.public)
        self.assertEqual(repository2.archived_timestamp,
                         repository1.archived_timestamp)

    def test_archive_no_save(self):
        """Testing Repository.archive with save=False"""
        repository1 = self.repository

        repository1.archive(save=False)
        self.assertTrue(repository1.name.startswith('ar:Git test repo:'))
        self.assertTrue(repository1.archived)
        self.assertFalse(repository1.public)
        self.assertIsNotNone(repository1.archived_timestamp)

        repository2 = Repository.objects.get(pk=repository1.pk)
        self.assertNotEqual(repository2.name,
                            repository1.name)
        self.assertNotEqual(repository2.archived,
                            repository1.archived)
        self.assertNotEqual(repository2.public,
                            repository1.public)
        self.assertNotEqual(repository2.archived_timestamp,
                            repository1.archived_timestamp)

    def test_clean_without_conflict(self):
        """Testing Repository.clean without name/path conflicts"""
        with self.assertNumQueries(1):
            self.repository.clean()

    def test_clean_with_name_conflict(self):
        """Testing Repository.clean with name conflict"""
        repository = Repository(name=self.repository.name,
                                path='path/to/repo.git',
                                tool=self.repository.tool,
                                scmtool_id=self.repository.scmtool_id)

        with self.assertRaises(ValidationError) as ctx:
            with self.assertNumQueries(1):
                repository.clean()

        self.assertEqual(ctx.exception.message_dict, {
            'name': ['A repository with this name already exists'],
        })

    def test_clean_with_path_conflict(self):
        """Testing Repository.clean with path conflict"""
        repository = Repository(name='New test repo',
                                path=self.repository.path,
                                tool=self.repository.tool,
                                scmtool_id=self.repository.scmtool_id)

        with self.assertRaises(ValidationError) as ctx:
            with self.assertNumQueries(1):
                repository.clean()

        self.assertEqual(ctx.exception.message_dict, {
            'path': ['A repository with this path already exists'],
        })

    def test_clean_with_name_and_path_conflict(self):
        """Testing Repository.clean with name and path conflict"""
        repository = Repository(name=self.repository.name,
                                path=self.repository.path,
                                tool=self.repository.tool,
                                scmtool_id=self.repository.scmtool_id)

        with self.assertRaises(ValidationError) as ctx:
            with self.assertNumQueries(1):
                repository.clean()

        self.assertEqual(ctx.exception.message_dict, {
            'name': ['A repository with this name already exists'],
            'path': ['A repository with this path already exists'],
        })

    def test_clean_with_path_conflict_with_archived(self):
        """Testing Repository.clean with archived repositories ignored for
        path conflict
        """
        orig_repository = self.repository
        orig_repository.archive()

        repository = Repository(name='New test repo',
                                path=orig_repository.path,
                                tool=orig_repository.tool,
                                scmtool_id=self.repository.scmtool_id)

        with self.assertNumQueries(1):
            repository.clean()

    def test_get_file_with_context(self):
        """Testing Repository.get_file with context="""
        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.get_file,
                    owner=scmtool_cls,
                    op=kgb.SpyOpReturn(b'data'))

        context = FileLookupContext(base_commit_id='def456')

        repository.get_file(path='readme',
                            revision='abc123',
                            context=context)

        self.assertSpyCalledWith(
            scmtool_cls.get_file,
            'readme',
            revision='abc123',
            base_commit_id='def456',
            context=context)

    def test_get_file_caching(self):
        """Testing Repository.get_file caches result"""
        path = 'readme'
        revision = 'abc123'
        base_commit_id = 'def456'

        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.get_file,
                    owner=scmtool_cls,
                    op=kgb.SpyOpReturn(b'file data'))

        # Two requests to the same path/revision should result in one only
        # call.
        data1 = repository.get_file(path=path,
                                    revision=revision)
        data2 = repository.get_file(path=path,
                                    revision=revision,
                                    context=FileLookupContext())

        self.assertIsInstance(data1, bytes)
        self.assertIsInstance(data2, bytes)
        self.assertEqual(data1, b'file data')
        self.assertEqual(data1, data2)
        self.assertSpyCallCount(scmtool_cls.get_file, 1)
        self.assertSpyLastCalledWith(scmtool_cls.get_file,
                                     path,
                                     revision=revision,
                                     base_commit_id=None)

        # A base commit ID should result in a new call.
        data3 = repository.get_file(path=path,
                                    revision=revision,
                                    base_commit_id=base_commit_id)

        self.assertEqual(data3, data1)
        self.assertSpyCallCount(scmtool_cls.get_file, 2)
        self.assertSpyLastCalledWith(scmtool_cls.get_file,
                                     path,
                                     revision=revision,
                                     base_commit_id=base_commit_id)

        # Another fetch with the same base_commit_id will use the cached
        # version, even if specified in a FileLookupContext.
        context = FileLookupContext(base_commit_id=base_commit_id)
        data4 = repository.get_file(path=path,
                                    revision=revision,
                                    context=context)

        self.assertEqual(data4, data1)
        self.assertSpyCallCount(scmtool_cls.get_file, 2)

    def test_get_file_signals(self):
        """Testing Repository.get_file emits signals"""
        def on_fetching_file(**kwargs):
            pass

        def on_fetched_file(**kwargs):
            pass

        repository = self.repository

        fetching_file.connect(on_fetching_file, sender=repository)
        fetched_file.connect(on_fetched_file, sender=repository)

        self.spy_on(on_fetching_file)
        self.spy_on(on_fetched_file)

        path = 'readme'
        revision = 'e965047'
        base_commit_id = 'def456'

        request = self.create_http_request()
        context = FileLookupContext(request=request,
                                    base_commit_id=base_commit_id)

        repository.get_file(path=path,
                            revision=revision,
                            context=context)

        self.assertSpyCalledWith(
            on_fetching_file,
            sender=repository,
            path=path,
            revision=revision,
            base_commit_id=base_commit_id,
            request=request,
            context=context)

        self.assertSpyCalledWith(
            on_fetched_file,
            sender=repository,
            path=path,
            revision=revision,
            base_commit_id=base_commit_id,
            request=request,
            context=context,
            data=b'Hello\n')

    def test_get_file_exists_caching_when_exists(self):
        """Testing Repository.get_file_exists caches result when exists"""
        path = 'readme'
        revision = 'e965047'
        base_commit_id = 'def456'

        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.file_exists,
                    owner=scmtool_cls,
                    op=kgb.SpyOpReturn(True))

        # Two requests to the same path/revision should result in one only
        # call.
        self.assertTrue(repository.get_file_exists(
            path=path,
            revision=revision))
        self.assertTrue(repository.get_file_exists(
            path=path,
            revision=revision,
            context=FileLookupContext()))

        self.assertSpyCallCount(scmtool_cls.file_exists, 1)
        self.assertSpyLastCalledWith(scmtool_cls.file_exists,
                                     path,
                                     revision=revision,
                                     base_commit_id=None)

        # A base commit ID should result in a new call.
        self.assertTrue(repository.get_file_exists(
            path=path,
            revision=revision,
            base_commit_id=base_commit_id))

        self.assertSpyCallCount(scmtool_cls.file_exists, 2)
        self.assertSpyLastCalledWith(scmtool_cls.file_exists,
                                     path,
                                     revision=revision,
                                     base_commit_id=base_commit_id)

        # Another check with the same base_commit_id will use the cached
        # version, even if specified in a FileLookupContext.
        context = FileLookupContext(base_commit_id=base_commit_id)
        self.assertTrue(repository.get_file_exists(
            path=path,
            revision=revision,
            context=context))

        self.assertSpyCallCount(scmtool_cls.file_exists, 2)

    def test_get_file_exists_caching_when_not_exists(self):
        """Testing Repository.get_file_exists doesn't cache result when the
        file does not exist
        """
        path = 'readme'
        revision = '12345'
        base_commit_id = 'def456'

        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.file_exists,
                    owner=scmtool_cls,
                    op=kgb.SpyOpReturn(False))

        context = FileLookupContext(base_commit_id=base_commit_id)

        self.assertFalse(repository.get_file_exists(
            path=path,
            revision=revision))
        self.assertFalse(repository.get_file_exists(
            path=path,
            revision=revision,
            context=FileLookupContext()))
        self.assertFalse(repository.get_file_exists(
            path=path,
            revision=revision,
            base_commit_id=base_commit_id))
        self.assertFalse(repository.get_file_exists(
            path=path,
            revision=revision,
            context=context))

        self.assertSpyCallCount(scmtool_cls.file_exists, 4)
        self.assertSpyCalledWith(
            scmtool_cls.file_exists.calls[0],
            path,
            revision=revision,
            base_commit_id=None)
        self.assertSpyCalledWith(
            scmtool_cls.file_exists.calls[1],
            path,
            revision=revision,
            base_commit_id=None)
        self.assertSpyCalledWith(
            scmtool_cls.file_exists.calls[2],
            path,
            revision=revision,
            base_commit_id=base_commit_id)
        self.assertSpyCalledWith(
            scmtool_cls.file_exists.calls[3],
            path,
            revision=revision,
            base_commit_id=base_commit_id,
            context=context)

    def test_get_file_exists_caching_with_fetched_file(self):
        """Testing Repository.get_file_exists uses get_file's cached result"""
        path = 'readme'
        revision = 'abc123'
        base_commit_id = 'def456'

        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.get_file,
                    owner=scmtool_cls,
                    op=kgb.SpyOpReturn(b'file data'))
        self.spy_on(scmtool_cls.file_exists,
                    owner=scmtool_cls,
                    op=kgb.SpyOpReturn(True))

        # These requests to the same path/revision should result in one only
        # call.
        repository.get_file(path=path,
                            revision=revision)
        self.assertTrue(repository.get_file_exists(
            path=path,
            revision=revision))
        self.assertTrue(repository.get_file_exists(
            path=path,
            revision=revision,
            context=FileLookupContext()))

        self.assertSpyCallCount(scmtool_cls.get_file, 1)
        self.assertSpyNotCalled(scmtool_cls.file_exists)

        # A base commit ID should result in a new call, which should then
        # persist for file checks.
        repository.get_file(path=path,
                            revision=revision,
                            base_commit_id=base_commit_id)
        self.assertTrue(repository.get_file_exists(
            path=path,
            revision=revision,
            base_commit_id=base_commit_id))
        self.assertTrue(repository.get_file_exists(
            path=path,
            revision=revision,
            context=FileLookupContext(base_commit_id=base_commit_id)))

        self.assertSpyCallCount(scmtool_cls.get_file, 2)
        self.assertSpyNotCalled(scmtool_cls.file_exists)

    def test_get_file_exists_signals(self):
        """Testing Repository.get_file_exists emits signals"""
        def on_checking(**kwargs):
            pass

        def on_checked(**kwargs):
            pass

        repository = self.repository

        checking_file_exists.connect(on_checking, sender=repository)
        checked_file_exists.connect(on_checked, sender=repository)

        self.spy_on(on_checking)
        self.spy_on(on_checked)

        path = 'readme'
        revision = 'e965047'
        base_commit_id = 'def456'

        request = self.create_http_request()
        context = FileLookupContext(request=request,
                                    base_commit_id=base_commit_id)

        repository.get_file_exists(path=path,
                                   revision=revision,
                                   context=context)

        self.assertSpyCalledWith(
            on_checking,
            sender=repository,
            path=path,
            revision=revision,
            base_commit_id=base_commit_id,
            request=request,
            context=context)

        self.assertSpyCalledWith(
            on_checked,
            sender=repository,
            path=path,
            revision=revision,
            base_commit_id=base_commit_id,
            request=request,
            context=context)

    def test_hosting_service(self):
        """Testing Repository.hosting_service with a valid hosting service"""
        account = HostingServiceAccount.objects.create(
            service_name=GitHub.hosting_service_id,
            username='foo')
        repository = self.create_repository(hosting_account=account)

        with self.assertNumQueries(0):
            self.assertIsInstance(repository.hosting_service, GitHub)

    def test_hosting_service_cannot_load(self):
        """Testing Repository.hosting_service with a hosting service
        that cannot be loaded
        """
        account = HostingServiceAccount.objects.create(
            service_name='blah',
            username='foo')
        repository = self.create_repository(hosting_account=account)
        message = ('The repository "Test Repo" cannot load the hosting '
                   'service "blah". An administrator should ensure all '
                   'necessary packages and extensions are installed.')

        with self.assertNumQueries(0):
            with self.assertRaisesMessage(MissingHostingServiceError, message):
                repository.hosting_service

    def test_repository_name_with_255_characters(self):
        """Testing Repository.name with 255 characters"""
        repository = self.create_repository(name='t' * 255)

        self.assertEqual(len(repository.name), 255)

    def test_is_accessible_by_with_public(self):
        """Testing Repository.is_accessible_by with public repository"""
        user = self.create_user()
        repository = self.create_repository()

        self.assertTrue(repository.is_accessible_by(user))
        self.assertTrue(repository.is_accessible_by(AnonymousUser()))

    def test_is_accessible_by_with_public_and_hidden(self):
        """Testing Repository.is_accessible_by with public hidden repository"""
        user = self.create_user()
        repository = self.create_repository(visible=False)

        self.assertTrue(repository.is_accessible_by(user))
        self.assertTrue(repository.is_accessible_by(AnonymousUser()))

    def test_is_accessible_by_with_private_and_not_member(self):
        """Testing Repository.is_accessible_by with private repository and
        user not a member
        """
        user = self.create_user()
        repository = self.create_repository(public=False)

        self.assertFalse(repository.is_accessible_by(user))
        self.assertFalse(repository.is_accessible_by(AnonymousUser()))

    def test_is_accessible_by_with_private_and_member(self):
        """Testing Repository.is_accessible_by with private repository and
        user is a member
        """
        user = self.create_user()
        repository = self.create_repository(public=False)
        repository.users.add(user)

        self.assertTrue(repository.is_accessible_by(user))

    def test_is_accessible_by_with_private_and_member_by_group(self):
        """Testing Repository.is_accessible_by with private repository and
        user is a member by group
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        repository = self.create_repository(public=False)
        repository.review_groups.add(group)

        self.assertTrue(repository.is_accessible_by(user))

    def test_is_accessible_by_with_private_and_superuser(self):
        """Testing Repository.is_accessible_by with private repository and
        user is a superuser
        """
        user = self.create_user(is_superuser=True)
        repository = self.create_repository(public=False)

        self.assertTrue(repository.is_accessible_by(user))

    def test_is_accessible_by_with_private_hidden_not_member(self):
        """Testing Repository.is_accessible_by with private hidden
        repository and user not a member
        """
        user = self.create_user()
        repository = self.create_repository(public=False,
                                            visible=False)

        self.assertFalse(repository.is_accessible_by(user))

    def test_is_accessible_by_with_private_hidden_and_member(self):
        """Testing Repository.is_accessible_by with private hidden
        repository and user is a member
        """
        user = self.create_user()

        repository = self.create_repository(public=False,
                                            visible=False)
        repository.users.add(user)

        self.assertTrue(repository.is_accessible_by(user))

    def test_is_accessible_by_with_private_hidden_and_member_by_group(self):
        """Testing Repository.is_accessible_by with private hidden
        repository and user is a member
        """
        user = self.create_user()

        group = self.create_review_group(invite_only=True)
        group.users.add(user)

        repository = self.create_repository(public=False,
                                            visible=False)
        repository.review_groups.add(group)

        self.assertTrue(repository.is_accessible_by(user))

    def test_is_accessible_by_with_private_hidden_and_superuser(self):
        """Testing Repository.is_accessible_by with private hidden
        repository and superuser
        """
        user = self.create_user(is_superuser=True)
        repository = self.create_repository(public=False,
                                            visible=False)

        self.assertTrue(repository.is_accessible_by(user))

    @add_fixtures(['test_users', 'test_site'])
    def test_is_accessible_by_with_local_site_accessible(self):
        """Testing Repository.is_accessible_by with Local Site accessible by
        user
        """
        user = self.create_user()

        repository = self.create_repository(with_local_site=True)
        repository.local_site.users.add(user)

        self.assertTrue(repository.is_accessible_by(user))

    @add_fixtures(['test_users', 'test_site'])
    def test_is_accessible_by_with_local_site_not_accessible(self):
        """Testing Repository.is_accessible_by with Local Site not accessible
        by user
        """
        user = self.create_user()
        repository = self.create_repository(with_local_site=True)

        self.assertFalse(repository.is_accessible_by(user))
        self.assertFalse(repository.is_accessible_by(AnonymousUser()))

    def test_scmtool_class(self):
        """Testing Repository.scmtool_class"""
        with self.assertNumQueries(0):
            repository = Repository(scmtool_id='git')

            self.assertIs(repository.scmtool_class, GitTool)

    def test_scmtool_class_with_unset_scmtool_id(self):
        """Testing Repository.scmtool_class with unset scmtool_id and with
        legacy tool_id
        """
        tool = Tool.objects.get(name='Git')

        # 1 query:
        #
        # 1. Insert new repository.
        queries = [
            {
                'type': 'INSERT',
                'model': Repository,
            },
        ]

        with self.assertQueries(queries):
            repository = Repository.objects.create(name='test-repo',
                                                   tool=tool)

            self.assertIs(repository.scmtool_class, GitTool)
            self.assertEqual(repository.scmtool_id, 'git')

        # Make sure that persists.
        repository.refresh_from_db()

        with self.assertNumQueries(0):
            self.assertIs(repository.scmtool_class, GitTool)
            self.assertEqual(repository.scmtool_id, 'git')

    def test_scmtool_class_with_unset_scmtool_id_deferred(self):
        """Testing Repository.scmtool_class with unset scmtool_id and with
        legacy tool_id and deferred fields
        """
        tool = Tool.objects.get(name='Git')
        repository = Repository.objects.create(name='test-repo',
                                               tool=tool)
        repository.scmtool_id = None
        repository.save(update_fields=('scmtool_id',))

        # Re-fetch with deferred fields.
        #
        # We are making sure this doesn't trigger a scmtool_id or tool_id
        # lookup.
        #
        # 1 query:
        #
        # 1. Fetch id, name for repository.
        queries = [
            {
                'model': Repository,
                'where': Q(pk=repository.pk),
                'only_fields': {'id', 'name'},
            },
        ]

        with self.assertQueries(queries):
            repository = (
                Repository.objects.filter(pk=repository.pk)
                .only('pk', 'name')
                .get()
            )

        # This direct access will trigger such a lookup, but the value should
        # be None.
        #
        # 1 query:
        #
        # 1. Fetch scmtool_id for repository.
        queries = [
            {
                'model': Repository,
                'where': Q(pk=repository.pk),
                'only_fields': {'scmtool_id'},
            },
        ]

        with self.assertQueries(queries):
            self.assertIsNone(repository.scmtool_id)

    def test_scmtool_class_with_unset_scmtool_id_on_new_repo(self):
        """Testing Repository.scmtool_class with unset scmtool_id and with
        legacy tool_id on new (unsaved) repository
        """
        tool = Tool.objects.get(name='Git')

        with self.assertNumQueries(0):
            repository = Repository(tool=tool)

            self.assertIs(repository.scmtool_class, GitTool)
            self.assertEqual(repository.scmtool_id, 'git')
            self.assertIsNone(repository.pk)

    def test_scmtool_class_with_unset_scmtool_id_and_missing_scmtool(self):
        """Testing Repository.scmtool_class with unset scmtool_id and with
        legacy tool_id and missing SCMTool
        """
        from reviewboard.scmtools.signal_handlers import logger

        tool = Tool.objects.create(name='XXX', class_name='x.x.x.Tool')

        # 1 query:
        #
        # 1. Insert new repository.
        queries = [
            {
                'type': 'INSERT',
                'model': Repository,
            },
        ]

        with self.assertLogs(logger) as logs:
            with self.assertQueries(queries):
                repository = Repository.objects.create(name='test-repo',
                                                       tool=tool)

        self.assertEqual(logs.output, [
            'ERROR:reviewboard.scmtools.signal_handlers:Attempted to upgrade '
            'the SCMTool state for repository ID None, but the SCMTool "XXX" '
            'could not be loaded: Error importing SCM Tool x.x.x: '
            '"No module named \'x\'"',
        ])

        message = (
            'There was an error loading the SCMTool "XXX" needed by this '
            'repository. The administrator should ensure all necessary '
            'packages and extensions are installed.'
        )

        with self.assertNumQueries(0):
            with self.assertRaisesMessage(ImproperlyConfigured, message):
                repository.scmtool_class

        self.assertIsNone(repository.scmtool_id)

    def test_scmtool_class_with_unset_scmtool_id_and_no_tool(self):
        """Testing Repository.scmtool_class with scmtool_id and without
        legacy tool_id
        """
        with self.assertNumQueries(0):
            repository = Repository()

            self.assertIsNone(repository.scmtool_class)

    def test_scmtool_class_with_unregistered_scmtool_id(self):
        """Testing Repository.scmtool_class with unregistered SCMTool"""
        from reviewboard.scmtools.models import logger

        tool = Tool.objects.create(name='XXX', class_name='x.x.x.Tool')

        # 1 query:
        #
        # 1. Insert new repository.
        queries = [
            {
                'type': 'INSERT',
                'model': Repository,
            },
        ]

        with self.assertQueries(queries):
            repository = Repository.objects.create(name='test-repo',
                                                   tool=tool,
                                                   scmtool_id='xxxtool')

        message = (
            'There was an error loading the SCMTool "xxxtool" needed by this '
            'repository. The administrator should ensure all necessary '
            'packages and extensions are installed.'
        )

        with self.assertNumQueries(0):
            with self.assertRaisesMessage(ImproperlyConfigured, message):
                with self.assertLogs(logger) as logs:
                    repository.scmtool_class

        self.assertEqual(logs.output, [
            'ERROR:reviewboard.scmtools.models:Error finding registered '
            'SCMTool "xxxtool" in repository ID 2.',
        ])
