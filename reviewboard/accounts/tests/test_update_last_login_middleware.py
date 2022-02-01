"""Unit tests for reviewboard.accounts.middleware.UpdateLastLoginMiddleware."""

from __future__ import unicode_literals

from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.test.client import RequestFactory
from django.utils import timezone
from kgb import SpyAgency

from reviewboard.accounts.middleware import UpdateLastLoginMiddleware
from reviewboard.testing import TestCase


class UpdateLastLoginMiddlewareTests(SpyAgency, TestCase):
    """Unit tests for UpdateLastLoginMiddleware."""

    fixtures = ['test_users']

    def setUp(self):
        super(UpdateLastLoginMiddlewareTests, self).setUp()

        self.middleware = UpdateLastLoginMiddleware()
        self.user = User.objects.create(username='test-user')

        self.request = RequestFactory().get('/')
        self.request.user = self.user

        self.spy_on(timezone.now,
                    call_fake=lambda: datetime(year=2018, month=3, day=3,
                                               hour=19, minute=30, second=0,
                                               tzinfo=timezone.utc))

        self.now = timezone.now()

    def test_process_request_with_gt_30_mins(self):
        """Testing UpdateLastLoginMiddleware.process_request with last login
        time > 30 minutes old
        """
        self.user.last_login = self.now - timedelta(seconds=31 * 60)
        self.middleware.process_request(self.request)

        self.assertEqual(self.user.last_login, self.now)

        # Make sure this has saved.
        user = User.objects.get(pk=self.user.pk)
        self.assertEqual(user.last_login, self.now)

    def test_process_request_with_lt_30_mins(self):
        """Testing UpdateLastLoginMiddleware.process_request with last login
        time < 30 minutes old
        """
        cur_last_login = self.now - timedelta(seconds=15 * 60)
        self.user.last_login = cur_last_login
        self.middleware.process_request(self.request)

        self.assertEqual(self.user.last_login, cur_last_login)
