from django.conf import settings
from django.test import TestCase

from reviewboard.admin import checks


class UpdateTests(TestCase):
    """Tests for update required pages"""

    def tearDown(self):
        # Make sure we don't break further tests by resetting this fully.
        checks.reset_check_cache()

    def testManualUpdatesRequired(self):
        """Testing check_updates_required with valid configuration"""
        # NOTE: This is assuming the install is fine. It should be given
        #       that we set things like the uploaded path correctly to
        #       a known good directory before starting unit tests.
        updates_required = checks.check_updates_required()

        self.assertEqual(len(updates_required), 0)

    def testManualUpdatesRequiredBadUpload(self):
        """Testing check_updates_required with a bad upload directory"""
        old_media_root = settings.MEDIA_ROOT
        settings.MEDIA_ROOT = "/"
        checks.reset_check_cache()

        updates_required = checks.check_updates_required()
        settings.MEDIA_ROOT = old_media_root

        self.assertEqual(len(updates_required), 1)

        url, data = updates_required[0]
        self.assertEqual(url, "admin/manual-updates/media-upload-dir.html")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/manual_updates_required.html")
