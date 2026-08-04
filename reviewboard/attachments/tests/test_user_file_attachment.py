"""Unit tests for reviewboard.attachments.models.UserFileAttachment.

Version Added:
    7.0.3:
    This was split off from :py:mod:`reviewboard.attachments.tests`.
"""

from __future__ import annotations

import kgb
import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from django.contrib.auth.models import AnonymousUser, User
from reviewboard.attachments.forms import UploadUserFileForm
from reviewboard.attachments.tests.base import BaseFileAttachmentTestCase
from reviewboard.site.models import LocalSite

if TYPE_CHECKING:
    from typing import Any


class UserFileAttachmentTests(kgb.SpyAgency, BaseFileAttachmentTestCase):
    """Unit tests for reviewboard.attachments.models.UserFileAttachment.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

    default_expected_extra_data: dict[str, Any] = {
        BaseFileAttachmentTestCase.DEFINED_LOCAL_SITE_KEY: True,
    }

    def test_user_file_add_file_after_create(self) -> None:
        """Testing user FileAttachment create without initial file and
        adding file through update
        """
        user = User.objects.get(username='doc')

        form = UploadUserFileForm(files={})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)
        file_attachment.refresh_from_db()

        self.assertFalse(file_attachment.file)
        self.assertEqual(file_attachment.user, user)
        self.assertEqual(file_attachment.extra_data,
                         self.default_expected_extra_data)

        uploaded_file = self.make_uploaded_file()
        form = UploadUserFileForm(files={
            'path': uploaded_file,
        })
        self.assertTrue(form.is_valid())

        file_attachment = form.update(file_attachment)
        file_attachment.refresh_from_db()

        self.assertTrue(os.path.basename(file_attachment.file.name).endswith(
            '__logo.png'))
        self.assertEqual(file_attachment.mimetype, 'image/png')

    def test_user_file_with_upload_file(self) -> None:
        """Testing user FileAttachment create with initial file"""
        user = User.objects.get(username='doc')
        uploaded_file = self.make_uploaded_file()

        form = UploadUserFileForm(files={
            'path': uploaded_file,
        })
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)

        self.assertEqual(file_attachment.user, user)
        self.assertTrue(os.path.basename(file_attachment.file.name).endswith(
            '__logo.png'))
        self.assertEqual(file_attachment.mimetype, 'image/png')
        self.assertEqual(file_attachment.extra_data,
                         self.default_expected_extra_data)

    def test_user_file_with_extra_data(self) -> None:
        """Testing user FileAttachment create with extra data"""
        class TestObject():
            def to_json(self):
                return {
                    'foo': 'bar'
                }

        user = User.objects.get(username='doc')
        uploaded_file = self.make_uploaded_file()

        form = UploadUserFileForm(
            data={
                'extra_data': {
                    'test_bool': True,
                    'test_date': datetime(2023, 1, 26, 5, 30, 3, 123456),
                    'test_int': 1,
                    'test_list': [1, 2, 3],
                    'test_nested_dict': {
                        'foo': 2,
                        'bar': 'baz',
                    },
                    'test_none': None,
                    'test_obj': TestObject(),
                    'test_str': 'test',
                }
            },
            files={'path': uploaded_file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.user, user)
        self.assertTrue(os.path.basename(file_attachment.file.name).endswith(
            '__logo.png'))
        self.assertEqual(file_attachment.mimetype, 'image/png')
        self.assertEqual(file_attachment.extra_data, {
            'test_bool': True,
            'test_date': '2023-01-26T05:30:03.123',
            'test_int': 1,
            'test_list': [1, 2, 3],
            'test_nested_dict': {
                'foo': 2,
                'bar': 'baz',
            },
            'test_none': None,
            'test_obj': {
                'foo': 'bar',
            },
            'test_str': 'test',
            **self.default_expected_extra_data,
        })

    def test_user_file_with_extra_data_string(self) -> None:
        """Testing user FileAttachment create with extra data passed as a
        JSON string
        """
        user = User.objects.get(username='doc')
        uploaded_file = self.make_uploaded_file()

        form = UploadUserFileForm(
            data={
                'extra_data': json.dumps({
                    'test_bool': True,
                    'test_int': 1,
                    'test_list': [1, 2, 3],
                    'test_nested_dict': {
                        'foo': 2,
                        'bar': 'baz',
                    },
                    'test_none': None,
                    'test_str': 'test',
                })
            },
            files={'path': uploaded_file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data, {
            'test_bool': True,
            'test_int': 1,
            'test_list': [1, 2, 3],
            'test_nested_dict': {
                'foo': 2,
                'bar': 'baz',
            },
            'test_none': None,
            'test_str': 'test',
            **self.default_expected_extra_data,
        })

    def test_user_file_with_extra_data_empties(self) -> None:
        """Testing user FileAttachment create with extra data that contains
        empty values
        """
        user = User.objects.get(username='doc')
        uploaded_file = self.make_uploaded_file()

        form = UploadUserFileForm(
            data={
                'extra_data': {}
            },
            files={'path': uploaded_file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data,
                         self.default_expected_extra_data)

        form = UploadUserFileForm(
            data={
                'extra_data': json.dumps(None)
            },
            files={'path': uploaded_file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data,
                         self.default_expected_extra_data)

        form = UploadUserFileForm(
            data={
                'extra_data': None
            },
            files={'path': uploaded_file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data,
                         self.default_expected_extra_data)

        form = UploadUserFileForm(
            data={
                'extra_data': {
                    'test_list': [],
                    'test_nested_dict': {},
                    'test_none': None,
                    'test_str': '',
                }
            },
            files={'path': uploaded_file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data, {
            'test_list': [],
            'test_nested_dict': {},
            'test_none': None,
            'test_str': '',
            **self.default_expected_extra_data,
        })

    def test_user_file_local_sites(self) -> None:
        """Testing user FileAttachment create with local site"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.get(name='local-site-1')

        form = UploadUserFileForm(files={})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user, local_site)

        self.assertEqual(file_attachment.user, user)
        self.assertEqual(file_attachment.local_site, local_site)

    def test_user_file_update_with_extra_data(self) -> None:
        """Testing user FileAttachment update with extra data"""
        class TestObject():
            def to_json(self) -> None:
                return {
                    'foo': 'bar'
                }

        user = User.objects.get(username='doc')
        uploaded_file = self.make_uploaded_file()

        form = UploadUserFileForm(files={'path': uploaded_file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create(user)
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data,
                         self.default_expected_extra_data)

        form = UploadUserFileForm(
            data={
                'extra_data': {
                    'test_bool': True,
                    'test_date': datetime(2023, 1, 26, 5, 30, 3, 123456),
                    'test_int': 1,
                    'test_list': [1, 2, 3],
                    'test_nested_dict': {
                        'foo': 2,
                        'bar': 'baz',
                    },
                    'test_none': None,
                    'test_obj': TestObject(),
                    'test_str': 'test',
                }
            }
        )
        self.assertTrue(form.is_valid())

        file_attachment = form.update(file_attachment)
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data, {
            'test_bool': True,
            'test_date': '2023-01-26T05:30:03.123',
            'test_int': 1,
            'test_list': [1, 2, 3],
            'test_nested_dict': {
                'foo': 2,
                'bar': 'baz',
            },
            'test_none': None,
            'test_obj': {
                'foo': 'bar',
            },
            'test_str': 'test',
            **self.default_expected_extra_data,
        })

    def test_user_file_is_accessible_by(self) -> None:
        """Testing user FileAttachment.is_accessible_by"""
        creating_user = User.objects.get(username='doc')
        admin_user = User.objects.get(username='admin')
        same_site_user = User.objects.get(username='dopey')
        different_site_user = User.objects.get(username='grumpy')

        local_site = LocalSite.objects.get(name='local-site-1')
        local_site.users.add(same_site_user)

        form = UploadUserFileForm(files={})
        self.assertTrue(form.is_valid())
        file_attachment = form.create(creating_user, local_site)

        self.assertTrue(file_attachment.is_accessible_by(admin_user))
        self.assertTrue(file_attachment.is_accessible_by(creating_user))
        self.assertFalse(file_attachment.is_accessible_by(AnonymousUser()))
        self.assertFalse(file_attachment.is_accessible_by(same_site_user))
        self.assertFalse(file_attachment.is_accessible_by(different_site_user))

    def test_user_file_is_mutable_by(self) -> None:
        """Testing user FileAttachment.is_mutable_by"""
        creating_user = User.objects.get(username='doc')
        admin_user = User.objects.get(username='admin')
        same_site_user = User.objects.get(username='dopey')
        different_site_user = User.objects.get(username='grumpy')

        local_site = LocalSite.objects.get(name='local-site-1')
        local_site.users.add(same_site_user)

        form = UploadUserFileForm(files={})
        self.assertTrue(form.is_valid())
        file_attachment = form.create(creating_user, local_site)

        self.assertTrue(file_attachment.is_mutable_by(admin_user))
        self.assertTrue(file_attachment.is_mutable_by(creating_user))
        self.assertFalse(file_attachment.is_mutable_by(AnonymousUser()))
        self.assertFalse(file_attachment.is_mutable_by(same_site_user))
        self.assertFalse(file_attachment.is_mutable_by(different_site_user))

    def test_get_absolute_url(self) -> None:
        """Testing user FileAttachment.get_absolute_url"""
        user = User.objects.get(username='doc')

        form = UploadUserFileForm(files={})
        self.assertTrue(form.is_valid())
        file_attachment = form.create(user, None)

        self.assertEqual(
            file_attachment.get_absolute_url(),
            f'http://example.com/users/{user.username}/'
            f'file-attachments/{file_attachment.uuid}/')

    def test_get_absolute_url_with_local_site(self) -> None:
        """Testing user FileAttachment.get_absolute_url with a local site"""
        user = User.objects.get(username='doc')
        local_site = LocalSite.objects.get(name='local-site-1')

        form = UploadUserFileForm(files={})
        self.assertTrue(form.is_valid())
        file_attachment = form.create(user, local_site)

        self.assertEqual(
            file_attachment.get_absolute_url(),
            f'http://example.com/s/{local_site.name}/users/{user.username}/'
            f'file-attachments/{file_attachment.uuid}/')

    def test_get_local_site(self) -> None:
        """Testing FileAttachment.get_local_site returns the stored local site
        """
        expected_local_site = self.get_local_site(self.local_site_name)
        user = User.objects.get(username='doc')
        file_attachment = self.create_user_file_attachment(
            user=user,
            local_site=expected_local_site)

        self.spy_on(file_attachment.get_review_request)

        with self.assertNumQueries(0):
            local_site = file_attachment.get_local_site()

        self.assertEqual(local_site, expected_local_site)
        self.assertIsNotNone(local_site)
        self.assertSpyNotCalled(file_attachment.get_review_request)

    def test_get_local_site_none(self) -> None:
        """Testing FileAttachment.get_local_site with local site set to None"""
        user = User.objects.get(username='doc')
        file_attachment = self.create_user_file_attachment(
            user=user)

        with self.assertNumQueries(0):
            local_site = file_attachment.get_local_site()

        self.assertIsNone(local_site)
