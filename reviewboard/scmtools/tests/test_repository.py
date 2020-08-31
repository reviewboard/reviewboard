from __future__ import unicode_literals

import os

from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ValidationError
from djblets.testing.decorators import add_fixtures
from kgb import SpyAgency

from reviewboard.scmtools.core import HEAD
from reviewboard.scmtools.models import Repository, Tool
from reviewboard.scmtools.signals import (checked_file_exists,
                                          checking_file_exists,
                                          fetched_file, fetching_file)
from reviewboard.testing.testcase import TestCase


class RepositoryTests(SpyAgency, TestCase):
    """Unit tests for Repository operations."""

    fixtures = ['test_scmtools']

    def setUp(self):
        super(RepositoryTests, self).setUp()

        self.local_repo_path = os.path.join(os.path.dirname(__file__),
                                            '..', 'testdata', 'git_repo')
        self.repository = Repository.objects.create(
            name='Git test repo',
            path=self.local_repo_path,
            tool=Tool.objects.get(name='Git'))

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
                                tool=self.repository.tool)

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
                                tool=self.repository.tool)

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
                                tool=self.repository.tool)

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
                                tool=orig_repository.tool)

        with self.assertNumQueries(1):
            repository.clean()

    def test_get_file_caching(self):
        """Testing Repository.get_file caches result"""
        path = 'readme'
        revision = 'e965047'

        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.get_file,
                    call_fake=lambda *args, **kwargs: b'file data',
                    owner=scmtool_cls)

        data1 = repository.get_file(path, revision)
        data2 = repository.get_file(path, revision)

        self.assertIsInstance(data1, bytes)
        self.assertIsInstance(data2, bytes)
        self.assertEqual(data1, b'file data')
        self.assertEqual(data1, data2)
        self.assertEqual(len(scmtool_cls.get_file.calls), 1)
        self.assertSpyCalledWith(scmtool_cls.get_file,
                                 path,
                                 revision=revision)

    def test_get_file_signals(self):
        """Testing Repository.get_file emits signals"""
        def on_fetching_file(sender, path, revision, request, **kwargs):
            found_signals.append(('fetching_file', path, revision, request))

        def on_fetched_file(sender, path, revision, request, **kwargs):
            found_signals.append(('fetched_file', path, revision, request))

        found_signals = []

        fetching_file.connect(on_fetching_file, sender=self.repository)
        fetched_file.connect(on_fetched_file, sender=self.repository)

        path = 'readme'
        revision = 'e965047'
        request = {}

        self.repository.get_file(path, revision, request=request)

        self.assertEqual(len(found_signals), 2)
        self.assertEqual(found_signals[0],
                         ('fetching_file', path, revision, request))
        self.assertEqual(found_signals[1],
                         ('fetched_file', path, revision, request))

    def test_get_file_exists_caching_when_exists(self):
        """Testing Repository.get_file_exists caches result when exists"""
        path = 'readme'
        revision = 'e965047'

        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.file_exists,
                    call_fake=lambda *args, **kwargs: True,
                    owner=scmtool_cls)

        self.assertTrue(repository.get_file_exists(path, revision))
        self.assertTrue(repository.get_file_exists(path, revision))

        self.assertEqual(len(scmtool_cls.file_exists.calls), 1)
        self.assertSpyCalledWith(scmtool_cls.file_exists,
                                 path,
                                 revision=revision)

    def test_get_file_exists_caching_when_not_exists(self):
        """Testing Repository.get_file_exists doesn't cache result when the
        file does not exist
        """
        path = 'readme'
        revision = '12345'

        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.file_exists,
                    call_fake=lambda *args, **kwargs: False,
                    owner=scmtool_cls)

        self.assertFalse(repository.get_file_exists(path, revision))
        self.assertFalse(repository.get_file_exists(path, revision))

        self.assertEqual(len(scmtool_cls.file_exists.calls), 2)
        self.assertSpyCalledWith(scmtool_cls.file_exists,
                                 path,
                                 revision=revision)

    def test_get_file_exists_caching_with_fetched_file(self):
        """Testing Repository.get_file_exists uses get_file's cached result"""
        path = 'readme'
        revision = 'e965047'

        repository = self.repository
        scmtool_cls = repository.scmtool_class

        self.spy_on(scmtool_cls.get_file,
                    call_fake=lambda *args, **kwargs: b'file data',
                    owner=scmtool_cls)
        self.spy_on(scmtool_cls.file_exists,
                    call_fake=lambda *args, **kwargs: True,
                    owner=scmtool_cls)

        repository.get_file(path, revision)
        exists1 = repository.get_file_exists(path, revision)
        exists2 = repository.get_file_exists(path, revision)

        self.assertTrue(exists1)
        self.assertTrue(exists2)
        self.assertEqual(len(scmtool_cls.get_file.calls), 1)
        self.assertEqual(len(scmtool_cls.file_exists.calls), 0)

    def test_get_file_exists_signals(self):
        """Testing Repository.get_file_exists emits signals"""
        def on_checking(sender, path, revision, request, **kwargs):
            found_signals.append(('checking_file_exists', path,
                                  revision, request))

        def on_checked(sender, path, revision, request, **kwargs):
            found_signals.append(('checked_file_exists', path,
                                  revision, request))

        repository = self.repository
        found_signals = []

        checking_file_exists.connect(on_checking, sender=repository)
        checked_file_exists.connect(on_checked, sender=repository)

        path = 'readme'
        revision = 'e965047'
        request = {}

        repository.get_file_exists(path, revision, request=request)

        self.assertEqual(len(found_signals), 2)
        self.assertEqual(found_signals[0],
                         ('checking_file_exists', path, revision, request))
        self.assertEqual(found_signals[1],
                         ('checked_file_exists', path, revision, request))

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
