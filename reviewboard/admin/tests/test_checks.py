"""Unit tests for reviewboard.admin.checks."""

from __future__ import unicode_literals

from django.conf import settings
from djblets.siteconfig.models import SiteConfiguration

from reviewboard.admin import checks
from reviewboard.testing.testcase import TestCase


class ChecksTests(TestCase):
    """Unit tests for reviewboard.admin.checks."""

    def setUp(self):
        super(ChecksTests, self).setUp()

        self.old_media_root = settings.MEDIA_ROOT

    def tearDown(self):
        super(ChecksTests, self).tearDown()

        # Make sure we don't break further tests by resetting this fully.
        checks.reset_check_cache()

        # If test_manual_updates_bad_upload failed in the middle, it could
        # neglect to fix the MEDIA_ROOT, which will break a bunch of future
        # tests. Make sure it's always what we expect.
        settings.MEDIA_ROOT = self.old_media_root
        siteconfig = SiteConfiguration.objects.get_current()
        siteconfig.set('site_media_root', self.old_media_root)
        siteconfig.save()

    def test_check_updates_required_with_no_updates(self):
        """Testing check_updates_required with valid configuration"""
        # NOTE: This is assuming the install is fine. It should be given
        #       that we set things like the uploaded path correctly to
        #       a known good directory before starting unit tests.
        updates_required = checks.check_updates_required()

        self.assertEqual(len(updates_required), 0)

    def test_check_updates_required_with_bad_upload(self):
        """Testing check_updates_required with a bad upload directory"""
        settings.MEDIA_ROOT = "/"
        checks.reset_check_cache()

        with self.siteconfig_settings({'site_media_root': '/'},
                                      reload_settings=False):
            updates_required = checks.check_updates_required()
            self.assertEqual(len(updates_required), 2)

            url, data = updates_required[0]
            self.assertEqual(url,
                             'admin/manual-updates/media-upload-dir.html')

            response = self.client.get('/dashboard/')
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response,
                                    'admin/manual_updates_required.html')

        settings.MEDIA_ROOT = self.old_media_root

        # Make sure that the site works again once the media root is fixed.
        with self.siteconfig_settings({'site_media_root': self.old_media_root},
                                      reload_settings=False):
            response = self.client.get('/dashboard/')
            self.assertTemplateNotUsed(response,
                                       'admin/manual_updates_required.html')
