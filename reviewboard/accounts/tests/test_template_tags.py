"""Unit tests for reviewboard.accounts.templatetags.accounts."""

from __future__ import unicode_literals

from datetime import datetime

import pytz
from django.contrib.auth.models import AnonymousUser, User
from django.template import Context, Template
from django.test.client import RequestFactory
from django.utils.safestring import SafeText
from djblets.testing.decorators import add_fixtures

from reviewboard.testing import TestCase


class JSUserSessionInfoTests(TestCase):
    """Unit tests for {% js_user_session_info %}."""

    maxDiff = 100000

    def setUp(self):
        super(JSUserSessionInfoTests, self).setUp()

        self.user = self.create_user(username='test',
                                     first_name='Test',
                                     last_name='User',
                                     email='test@example.com')

    def test_with_anonymous_user(self):
        """Testing {% js_user_session_info %} with anonymous user"""
        self.assertJSONEqual(
            self._render_tag(AnonymousUser()),
            {
                'authenticated': False,
                'loginURL': '/account/login/',
            })

    def test_with_authenticated_user(self):
        """Testing {% js_user_session_info %} with authenticated user"""
        profile = self.user.get_profile()
        profile.timezone = 'US/Pacific'
        profile.save(update_fields=('timezone',))

        tz = pytz.timezone('US/Pacific')

        if tz.dst(datetime.now()):
            expected_tz_offset = '-0700'
        else:
            expected_tz_offset = '-0800'

        avatar_url = ('https://secure.gravatar.com/avatar/'
                      '55502f40dc8b7c769880b10874abc9d0')

        self.assertJSONEqual(
            self._render_tag(self.user),
            {
                'archivedReviewRequestsURL':
                    '/api/users/test/archived-review-requests/',
                'authenticated': True,
                'avatarHTML': {
                    '32': '<img src="https://secure.gravatar.com/avatar/'
                          '55502f40dc8b7c769880b10874abc9d0?s=32&d=mm"'
                          ' alt="Test User" width="32" height="32"'
                          ' srcset="https://secure.gravatar.com/avatar/'
                          '55502f40dc8b7c769880b10874abc9d0?s=32&d=mm 1x,'
                          ' https://secure.gravatar.com/avatar/'
                          '55502f40dc8b7c769880b10874abc9d0?s=64&d=mm 2x,'
                          ' https://secure.gravatar.com/avatar/'
                          '55502f40dc8b7c769880b10874abc9d0?s=96&d=mm 3x"'
                          ' class="avatar djblets-o-avatar">\n',
                },
                'avatarURLs': {
                    '32': {
                        '1x': '%s?s=32&d=mm' % avatar_url,
                        '2x': '%s?s=64&d=mm' % avatar_url,
                        '3x': '%s?s=96&d=mm' % avatar_url,
                    },
                },
                'commentsOpenAnIssue': True,
                'defaultUseRichText': True,
                'enableDesktopNotifications': True,
                'fullName': 'Test User',
                'mutedReviewRequestsURL':
                    '/api/users/test/muted-review-requests/',
                'readOnly': False,
                'sessionURL': '/api/session/',
                'timezoneOffset': expected_tz_offset,
                'userFileAttachmentsURL':
                    '/api/users/test/user-file-attachments/',
                'userPageURL': '/users/test/',
                'username': 'test',
                'watchedReviewGroupsURL':
                    '/api/users/test/watched/review-groups/',
                'watchedReviewRequestsURL':
                    '/api/users/test/watched/review-requests/',
            })

    @add_fixtures(['test_site'])
    def test_with_authenticated_user_and_local_site(self):
        """Testing {% js_user_session_info %} with authenticated user and
        LocalSite
        """
        profile = self.user.get_profile()
        profile.timezone = 'US/Pacific'
        profile.save(update_fields=('timezone',))

        tz = pytz.timezone('US/Pacific')

        if tz.dst(datetime.now()):
            expected_tz_offset = '-0700'
        else:
            expected_tz_offset = '-0800'

        local_site = self.get_local_site('local-site-1')

        avatar_url = ('https://secure.gravatar.com/avatar/'
                      '55502f40dc8b7c769880b10874abc9d0')

        self.assertJSONEqual(
            self._render_tag(self.user, local_site=local_site),
            {
                'archivedReviewRequestsURL':
                    '/s/local-site-1/api/users/test/archived-review-requests/',
                'authenticated': True,
                'avatarHTML': {
                    '32': '<img src="https://secure.gravatar.com/avatar/'
                          '55502f40dc8b7c769880b10874abc9d0?s=32&d=mm"'
                          ' alt="Test User" width="32" height="32"'
                          ' srcset="https://secure.gravatar.com/avatar/'
                          '55502f40dc8b7c769880b10874abc9d0?s=32&d=mm 1x,'
                          ' https://secure.gravatar.com/avatar/'
                          '55502f40dc8b7c769880b10874abc9d0?s=64&d=mm 2x,'
                          ' https://secure.gravatar.com/avatar/'
                          '55502f40dc8b7c769880b10874abc9d0?s=96&d=mm 3x"'
                          ' class="avatar djblets-o-avatar">\n',
                },
                'avatarURLs': {
                    '32': {
                        '1x': '%s?s=32&d=mm' % avatar_url,
                        '2x': '%s?s=64&d=mm' % avatar_url,
                        '3x': '%s?s=96&d=mm' % avatar_url,
                    },
                },
                'commentsOpenAnIssue': True,
                'defaultUseRichText': True,
                'enableDesktopNotifications': True,
                'fullName': 'Test User',
                'mutedReviewRequestsURL':
                    '/s/local-site-1/api/users/test/muted-review-requests/',
                'readOnly': False,
                'sessionURL': '/s/local-site-1/api/session/',
                'timezoneOffset': expected_tz_offset,
                'userFileAttachmentsURL':
                    '/s/local-site-1/api/users/test/user-file-attachments/',
                'userPageURL': '/s/local-site-1/users/test/',
                'username': 'test',
                'watchedReviewGroupsURL':
                    '/s/local-site-1/api/users/test/watched/review-groups/',
                'watchedReviewRequestsURL':
                    '/s/local-site-1/api/users/test/watched/review-requests/',
            })

    def test_with_authenticated_and_no_profile(self):
        """Testing {% js_user_session_info %} with authenticated user and
        no Profile
        """
        self.user.get_profile().delete()

        avatar_url = ('https://secure.gravatar.com/avatar/'
                      '55502f40dc8b7c769880b10874abc9d0')

        siteconfig_settings = {
            'default_use_rich_text': False,
        }

        with self.siteconfig_settings(siteconfig_settings):
            self.assertJSONEqual(
                self._render_tag(self.user),
                {
                    'archivedReviewRequestsURL':
                        '/api/users/test/archived-review-requests/',
                    'authenticated': True,
                    'avatarHTML': {
                        '32': '<img src="https://secure.gravatar.com/avatar/'
                              '55502f40dc8b7c769880b10874abc9d0?s=32&d=mm"'
                              ' alt="Test User" width="32" height="32"'
                              ' srcset="https://secure.gravatar.com/avatar/'
                              '55502f40dc8b7c769880b10874abc9d0?s=32&d=mm 1x,'
                              ' https://secure.gravatar.com/avatar/'
                              '55502f40dc8b7c769880b10874abc9d0?s=64&d=mm 2x,'
                              ' https://secure.gravatar.com/avatar/'
                              '55502f40dc8b7c769880b10874abc9d0?s=96&d=mm 3x"'
                              ' class="avatar djblets-o-avatar">\n',
                    },
                    'avatarURLs': {
                        '32': {
                            '1x': '%s?s=32&d=mm' % avatar_url,
                            '2x': '%s?s=64&d=mm' % avatar_url,
                            '3x': '%s?s=96&d=mm' % avatar_url,
                        },
                    },
                    'commentsOpenAnIssue': True,
                    'defaultUseRichText': False,
                    'enableDesktopNotifications': True,
                    'fullName': 'Test User',
                    'mutedReviewRequestsURL':
                        '/api/users/test/muted-review-requests/',
                    'readOnly': False,
                    'sessionURL': '/api/session/',
                    'timezoneOffset': '+0000',
                    'userFileAttachmentsURL':
                        '/api/users/test/user-file-attachments/',
                    'userPageURL': '/users/test/',
                    'username': 'test',
                    'watchedReviewGroupsURL':
                        '/api/users/test/watched/review-groups/',
                    'watchedReviewRequestsURL':
                        '/api/users/test/watched/review-requests/',
                })

    def test_with_authenticated_and_avatars_disabled(self):
        """Testing {% js_user_session_info %} with authenticated user and
        avatars disabled
        """
        siteconfig_settings = {
            'avatars_enabled': False,
        }

        with self.siteconfig_settings(siteconfig_settings):
            self.assertJSONEqual(
                self._render_tag(self.user),
                {
                    'archivedReviewRequestsURL':
                        '/api/users/test/archived-review-requests/',
                    'authenticated': True,
                    'avatarURLs': {},
                    'avatarHTML': {},
                    'commentsOpenAnIssue': True,
                    'defaultUseRichText': True,
                    'enableDesktopNotifications': True,
                    'fullName': 'Test User',
                    'mutedReviewRequestsURL':
                        '/api/users/test/muted-review-requests/',
                    'readOnly': False,
                    'sessionURL': '/api/session/',
                    'timezoneOffset': '+0000',
                    'userFileAttachmentsURL':
                        '/api/users/test/user-file-attachments/',
                    'userPageURL': '/users/test/',
                    'username': 'test',
                    'watchedReviewGroupsURL':
                        '/api/users/test/watched/review-groups/',
                    'watchedReviewRequestsURL':
                        '/api/users/test/watched/review-requests/',
                })

    def _render_tag(self, user, local_site=None):
        """Utility function to render the tag.

        This will render the template for the tag, providing all necessary
        arguments. It will also check the rendered string is of the expected
        type before returning it.

        Args:
            user (django.contrib.auth.models.User):
                The user to pass to the tag.

            local_site (reviewboard.site.models.LocalSite, optional):
                An optional Local Site for the request.

        Returns:
            django.utils.safestring.SafeText:
            The rendered content.
        """
        request = RequestFactory().get('/s/local-site-1/')
        request.user = user

        if local_site is not None:
            request._local_site_name = local_site.name
            request.local_site = local_site

        t = Template('{% load accounts %}'
                     '{% js_user_session_info %}')

        rendered = t.render(Context({
            'request': request,
        }))

        self.assertIsInstance(rendered, SafeText)

        return rendered


class UserProfileDisplayNameTests(TestCase):
    """Unit tests for {% user_profile_display_name %}."""

    def test_escapes_name(self):
        """Testing {% user_profile_display_name %} escapes content"""
        user = User.objects.create(
            username='test',
            first_name='"><script>alert("unsafe");</script>',
            last_name='<"',
            email='test@example.com')
        request_user = User.objects.create(username='admin',
                                           email='admin@example.com',
                                           is_superuser=True)
        rendered = self._render_tag(user, request_user)

        self.assertEqual(
            rendered,
            '&quot;&gt;&lt;script&gt;alert(&quot;unsafe&quot;);&lt;/script&gt;'
            ' &lt;&quot;')

    def _render_tag(self, user, request_user):
        """Utility function to render the tag.

        This will render the template for the tag, providing all necessary
        arguments. It will also check the rendered string is of the expected
        type before returning it.

        Args:
            user (django.contrib.auth.models.User):
                The user to pass to the tag.

            request_user (django.contrib.auth.models.User):
                The requesting user.

        Returns:
            django.utils.safestring.SafeText:
            The rendered content.
        """
        request = RequestFactory().get('/')
        request.user = request_user

        t = Template('{% load accounts %}'
                     '{% user_profile_display_name user %}')

        rendered = t.render(Context({
            'request': request,
            'user': user,
        }))

        self.assertIsInstance(rendered, SafeText)

        return rendered
