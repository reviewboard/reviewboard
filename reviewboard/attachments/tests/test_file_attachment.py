"""Unit tests for reviewboard.attachments.models.FileAttachment.

Version Added:
    7.0.3:
    This was split off from :py:mod:`reviewboard.attachments.tests`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

import kgb
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from djblets.testing.decorators import add_fixtures

from reviewboard.attachments.forms import UploadFileForm
from reviewboard.attachments.models import (FileAttachment,
                                            FileAttachmentHistory)
from reviewboard.attachments.tests.base import BaseFileAttachmentTestCase
from reviewboard.reviews.ui.image import ImageReviewUI


class FileAttachmentTests(kgb.SpyAgency, BaseFileAttachmentTestCase):
    """Unit tests for reviewboard.attachments.models.FileAttachment.

    Version Added:
        7.0.3:
        This was split off from :py:mod:`reviewboard.attachments.tests`.
    """

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file(self):
        """Testing uploading a file attachment"""
        review_request = self.create_review_request(publish=True)

        file = self.make_uploaded_file()
        form = UploadFileForm(review_request, files={
            'path': file,
        })
        self.assertTrue(form.is_valid())

        file_attachment = form.create()
        file_attachment.refresh_from_db()

        self.assertTrue(os.path.basename(file_attachment.file.name).endswith(
            '__logo.png'))
        self.assertEqual(file_attachment.mimetype, 'image/png')
        self.assertEqual(
            file_attachment.extra_data,
            {
                'sha256_checksum': ('1931a3b367e2913d28f9587dbd0ccf79b2c'
                                    '2225de7c47550dd1cc49085077e49'),
            })

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_with_history(self):
        """Testing uploading a file attachment to an existing
        FileAttachmentHistory
        """
        review_request_1 = self.create_review_request(publish=True)
        history = FileAttachmentHistory.objects.create(display_position=0)
        review_request_1.file_attachment_histories.add(history)

        file = self.make_uploaded_file()
        form = UploadFileForm(review_request_1,
                              data={'attachment_history': history.pk},
                              files={'path': file})
        self.assertTrue(form.is_valid())
        form.create()

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_with_history_mismatch(self):
        """Testing uploading a file attachment to an existing
        FileAttachmentHistory with a mismatched review request
        """
        review_request_1 = self.create_review_request(publish=True)
        review_request_2 = self.create_review_request(publish=True)
        uploaded_file = self.make_uploaded_file()

        history = FileAttachmentHistory.objects.create(display_position=0)
        review_request_1.file_attachment_histories.add(history)

        form = UploadFileForm(review_request_2,
                              data={'attachment_history': history.pk},
                              files={'path': uploaded_file})
        self.assertFalse(form.is_valid())

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_revisions(self):
        """Testing uploading multiple revisions of a file"""
        user = User.objects.create_user(username='testuser')
        review_request = self.create_review_request(publish=True,
                                                    target_people=[user])
        history = FileAttachmentHistory.objects.create(display_position=0)
        review_request.file_attachment_histories.add(history)
        uploaded_file = self.make_uploaded_file()

        # Add a file with the given history
        form = UploadFileForm(review_request,
                              data={'attachment_history': history.pk},
                              files={'path': uploaded_file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        history = FileAttachmentHistory.objects.get(pk=history.pk)
        self.assertEqual(file_attachment.attachment_revision, 1)
        self.assertEqual(history.latest_revision, 1)
        self.assertEqual(history.display_position, 0)

        review_request.get_draft().publish()
        # Post an update
        form = UploadFileForm(review_request,
                              data={'attachment_history': history.pk},
                              files={'path': uploaded_file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        history = FileAttachmentHistory.objects.get(pk=history.pk)
        self.assertEqual(file_attachment.attachment_revision, 2)
        self.assertEqual(history.latest_revision, 2)
        self.assertEqual(history.display_position, 0)

        review_request.get_draft().publish()

        # Post two updates without publishing the draft in between
        form = UploadFileForm(review_request,
                              data={'attachment_history': history.pk},
                              files={'path': uploaded_file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        history = FileAttachmentHistory.objects.get(pk=history.pk)
        self.assertEqual(file_attachment.attachment_revision, 3)
        self.assertEqual(history.latest_revision, 3)
        self.assertEqual(history.display_position, 0)

        form = UploadFileForm(review_request,
                              data={'attachment_history': history.pk},
                              files={'path': uploaded_file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        history = FileAttachmentHistory.objects.get(pk=history.pk)
        self.assertEqual(file_attachment.attachment_revision, 3)
        self.assertEqual(history.latest_revision, 3)
        self.assertEqual(history.display_position, 0)

        # Add another (unrelated) file to check display position
        form = UploadFileForm(review_request,
                              files={'path': uploaded_file})
        self.assertTrue(form.is_valid())
        file_attachment = form.create()
        self.assertEqual(file_attachment.attachment_revision, 1)
        self.assertEqual(file_attachment.attachment_history.latest_revision, 1)
        self.assertEqual(file_attachment.attachment_history.display_position,
                         1)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_with_extra_data(self):
        """Testing uploading a file attachment with extra data"""
        class TestObject():
            def to_json(self):
                return {
                    'foo': 'bar'
                }

        review_request = self.create_review_request(publish=True)

        file = self.make_uploaded_file()
        form = UploadFileForm(
            review_request,
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
            files={'path': file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create()
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data, {
            'sha256_checksum': ('1931a3b367e2913d28f9587dbd0ccf79b2c'
                                '2225de7c47550dd1cc49085077e49'),
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
        })

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_with_extra_data_string(self):
        """Testing uploading a file attachment with extra data passed as a
        JSON string
        """
        review_request = self.create_review_request(publish=True)

        file = self.make_uploaded_file()
        form = UploadFileForm(
            review_request,
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
            files={'path': file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create()
        file_attachment.refresh_from_db()

        self.assertEqual(file_attachment.extra_data, {
            'sha256_checksum': ('1931a3b367e2913d28f9587dbd0ccf79b2c'
                                '2225de7c47550dd1cc49085077e49'),
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

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_upload_file_with_extra_data_empties(self):
        """Testing uploading a file attachment with extra data that contains
        empty values
        """
        review_request = self.create_review_request(publish=True)
        file = self.make_uploaded_file()

        form = UploadFileForm(
            review_request,
            data={
                'extra_data': {}
            },
            files={'path': file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create()
        file_attachment.refresh_from_db()
        self.assertEqual(
            file_attachment.extra_data,
            {
                'sha256_checksum': ('1931a3b367e2913d28f9587dbd0ccf79b2c'
                                    '2225de7c47550dd1cc49085077e49'),
            })

        form = UploadFileForm(
            review_request,
            data={
                'extra_data': json.dumps(None)
            },
            files={'path': file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create()
        file_attachment.refresh_from_db()
        self.assertEqual(
            file_attachment.extra_data,
            {
                'sha256_checksum': ('1931a3b367e2913d28f9587dbd0ccf79b2c'
                                    '2225de7c47550dd1cc49085077e49'),
            })

        form = UploadFileForm(
            review_request,
            data={
                'extra_data': None
            },
            files={'path': file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create()
        file_attachment.refresh_from_db()
        self.assertEqual(
            file_attachment.extra_data,
            {
                'sha256_checksum': ('1931a3b367e2913d28f9587dbd0ccf79b2c'
                                    '2225de7c47550dd1cc49085077e49'),
            })

        form = UploadFileForm(
            review_request,
            data={
                'extra_data': {
                    'test_list': [],
                    'test_nested_dict': {},
                    'test_none': None,
                    'test_str': '',
                }
            },
            files={'path': file})
        self.assertTrue(form.is_valid())

        file_attachment = form.create()
        file_attachment.refresh_from_db()
        self.assertEqual(file_attachment.extra_data, {
            'sha256_checksum': ('1931a3b367e2913d28f9587dbd0ccf79b2c'
                                '2225de7c47550dd1cc49085077e49'),
            'test_list': [],
            'test_nested_dict': {},
            'test_none': None,
            'test_str': '',
        })

    def test_is_from_diff_with_no_association(self):
        """Testing FileAttachment.is_from_diff with standard attachment"""
        file_attachment = FileAttachment()

        self.assertFalse(file_attachment.is_from_diff)

    @add_fixtures(['test_scmtools'])
    def test_is_from_diff_with_repository(self):
        """Testing FileAttachment.is_from_diff with repository association"""
        repository = self.create_repository()
        file_attachment = FileAttachment(repository=repository)

        self.assertTrue(file_attachment.is_from_diff)

    @add_fixtures(['test_scmtools'])
    def test_is_from_diff_with_filediff(self):
        """Testing FileAttachment.is_from_diff with filediff association"""
        filediff = self.make_filediff()
        file_attachment = FileAttachment(added_in_filediff=filediff)

        self.assertTrue(file_attachment.is_from_diff)

    @add_fixtures(['test_users', 'test_scmtools'])
    def test_utf16_thumbnail(self):
        """Testing file attachment thumbnail generation for UTF-16 files"""
        filename = os.path.join(os.path.dirname(__file__),
                                'testdata', 'utf-16.txt')
        with open(filename, 'rb') as f:
            review_request = self.create_review_request(publish=True)

            file = SimpleUploadedFile(
                f.name,
                f.read(),
                content_type='text/plain;charset=utf-16le')
            form = UploadFileForm(review_request, files={'path': file})
            form.is_valid()

            file_attachment = form.create()

            self.assertEqual(
                file_attachment.thumbnail,
                '<div class="file-thumbnail"> <div class="file-thumbnail-clipp'
                'ed"><pre>UTF-16le encoded sample plain-text file</pre><pre>'
                '\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e'
                '\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e'
                '\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e'
                '\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e\u203e</pre>'
                '<pre></pre><pre>Markus Kuhn [\u02c8ma\u02b3k\u028as ku\u02d0'
                'n] &lt;http://www.cl.cam.ac.uk/~mgk25/&gt; \u2014 2002-07-25'
                '</pre><pre></pre><pre></pre><pre>The ASCII compatible UTF-8 '
                'encoding used in this plain-text file</pre><pre>is defined '
                'in Unicode, ISO 10646-1, and RFC 2279.</pre><pre></pre><pre>'
                '</pre><pre>Using Unicode/UTF-8, you can write in emails and '
                'source code things such as</pre><pre></pre><pre>Mathematics '
                'and sciences:</pre><pre></pre><pre>  \u222e E\u22c5da = Q,  '
                'n \u2192 \u221e, \u2211 f(i) = \u220f g(i),      \u23a7\u23a1'
                '\u239b\u250c\u2500\u2500\u2500\u2500\u2500\u2510\u239e\u23a4'
                '\u23ab</pre><pre>                                           '
                ' \u23aa\u23a2\u239c\u2502a\xb2+b\xb3 \u239f\u23a5\u23aa'
                '</pre><pre>  \u2200x\u2208</pre></div></div>')

    @add_fixtures(['test_users'])
    def test_is_review_ui_accessible_by_true(self) -> None:
        """Testing FileAttachment.is_review_ui_accessible_by with a user who
        can access the review UI
        """
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(submitter=user)
        file_attachment = self.create_file_attachment(
            review_request=review_request,
            mimetype='image/png')

        self.spy_on(ImageReviewUI.is_enabled_for, op=kgb.SpyOpReturn(True))

        self.assertTrue(file_attachment.is_review_ui_accessible_by(user=user))

    @add_fixtures(['test_users'])
    def test_is_review_ui_accessible_by_false(self) -> None:
        """Testing FileAttachment.is_review_ui_accessible_by with a user who
        cannot access the review UI
        """
        user = User.objects.get(username='doc')
        review_request = self.create_review_request(submitter=user)
        file_attachment = self.create_file_attachment(
            review_request=review_request,
            mimetype='image/png')

        self.spy_on(ImageReviewUI.is_enabled_for, op=kgb.SpyOpReturn(False))

        self.assertFalse(file_attachment.is_review_ui_accessible_by(user=user))

    def test_get_absolute_url(self) -> None:
        """Testing FileAttachment.get_absolute_url"""
        review_request = self.create_review_request()
        file_attachment = self.create_file_attachment(
            review_request=review_request,
            mimetype='image/png')

        self.assertEqual(
            file_attachment.get_absolute_url(),
            'http://example.com/r/1/file/1/download/')

    def test_get_absolute_url_with_local_site(self) -> None:
        """Testing FileAttachment.get_absolute_url with a local site"""
        review_request = self.create_review_request(with_local_site=True)
        local_site_name = review_request.local_site.name
        file_attachment = self.create_file_attachment(
            review_request=review_request,
            mimetype='image/png')

        self.assertEqual(
            file_attachment.get_absolute_url(),
            f'http://example.com/s/{local_site_name}/r/1001/file/1/download/')
