"""Unit tests for reviewboard.accounts.models.LocalSiteProfile."""

import kgb
from django.contrib.auth.models import User

from reviewboard.accounts.models import LocalSiteProfile
from reviewboard.testing import TestCase


class LocalSiteProfileTests(kgb.SpyAgency, TestCase):
    """Unit tests for reviewboard.accounts.models.LocalSiteProfile."""

    fixtures = ['test_users']

    def test_duplicate_profiles(self):
        """Testing LocalSiteProfileManager.for_user consolidation of duplicate
        profiles
        """
        user = User.objects.get(username='doc')
        profile = user.get_profile(create_if_missing=True)

        self.create_review_request(public=True, submitter=user)

        self.spy_on(LocalSiteProfile.objects._fix_duplicate_profiles)

        LocalSiteProfile.objects.create(user=user, profile=profile)
        LocalSiteProfile.objects.create(user=user, profile=profile)
        LocalSiteProfile.objects.create(
            user=user,
            profile=profile,
            permissions={'test': True})

        # Make sure we don't have any cached profiles.
        user._site_profiles = {}

        profile = user.get_site_profile(local_site=None)

        # Check merged profile data.
        self.assertEqual(profile.permissions, {'test': True})
        self.assertIsNone(profile.direct_incoming_request_count)
        self.assertIsNone(profile.total_incoming_request_count)
        self.assertIsNone(profile.pending_outgoing_request_count)
        self.assertIsNone(profile.total_outgoing_request_count)
        self.assertIsNone(profile.starred_public_request_count)

        # And make sure all those changes are persisted.
        profile.refresh_from_db()
        self.assertEqual(profile.permissions, {'test': True})
        self.assertEqual(profile.direct_incoming_request_count, 0)
        self.assertEqual(profile.total_incoming_request_count, 0)
        self.assertEqual(profile.pending_outgoing_request_count, 1)
        self.assertEqual(profile.total_outgoing_request_count, 1)
        self.assertEqual(profile.starred_public_request_count, 0)

        self.assertSpyCalled(LocalSiteProfile.objects._fix_duplicate_profiles)
