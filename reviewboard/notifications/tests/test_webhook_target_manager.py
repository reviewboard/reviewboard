from __future__ import unicode_literals

from djblets.testing.decorators import add_fixtures

from reviewboard.notifications.models import WebHookTarget
from reviewboard.site.models import LocalSite
from reviewboard.testing import TestCase


class WebHookTargetManagerTests(TestCase):
    """Unit tests for WebHookTargetManager."""

    ENDPOINT_URL = 'http://example.com/endpoint/'

    def test_for_event(self):
        """Testing WebHookTargetManager.for_event"""
        # These should not match.
        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        WebHookTarget.objects.create(
            events='event3',
            url=self.ENDPOINT_URL,
            enabled=False,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        # These should match.
        target1 = WebHookTarget.objects.create(
            events='event2,event3',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        target2 = WebHookTarget.objects.create(
            events='*',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        targets = WebHookTarget.objects.for_event('event3')
        self.assertEqual(targets, [target1, target2])

    def test_for_event_with_local_site(self):
        """Testing WebHookTargetManager.for_event with Local Sites"""
        site = LocalSite.objects.create(name='test-site')

        # These should not match.
        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=False,
            local_site=site,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        # This should match.
        target = WebHookTarget.objects.create(
            events='event1,event2',
            url=self.ENDPOINT_URL,
            enabled=True,
            local_site=site,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        targets = WebHookTarget.objects.for_event('event1',
                                                  local_site_id=site.pk)
        self.assertEqual(targets, [target])

    @add_fixtures(['test_scmtools'])
    def test_for_event_with_repository(self):
        """Testing WebHookTargetManager.for_event with repository"""
        repository1 = self.create_repository()
        repository2 = self.create_repository()

        # These should not match.
        unused_target1 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=False,
            apply_to=WebHookTarget.APPLY_TO_SELECTED_REPOS)
        unused_target1.repositories.add(repository2)

        unused_target2 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=False,
            apply_to=WebHookTarget.APPLY_TO_SELECTED_REPOS)
        unused_target2.repositories.add(repository1)

        WebHookTarget.objects.create(
            events='event3',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_NO_REPOS)

        # These should match.
        target1 = WebHookTarget.objects.create(
            events='event1,event2',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        target2 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_SELECTED_REPOS)
        target2.repositories.add(repository1)

        targets = WebHookTarget.objects.for_event('event1',
                                                  repository_id=repository1.pk)
        self.assertEqual(targets, [target1, target2])

    @add_fixtures(['test_scmtools'])
    def test_for_event_with_no_repository(self):
        """Testing WebHookTargetManager.for_event with no repository"""
        repository = self.create_repository()

        # These should not match.
        unused_target1 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_SELECTED_REPOS)
        unused_target1.repositories.add(repository)

        WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=False,
            apply_to=WebHookTarget.APPLY_TO_NO_REPOS)

        WebHookTarget.objects.create(
            events='event2',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_NO_REPOS)

        # These should match.
        target1 = WebHookTarget.objects.create(
            events='event1,event2',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_ALL)

        target2 = WebHookTarget.objects.create(
            events='event1',
            url=self.ENDPOINT_URL,
            enabled=True,
            apply_to=WebHookTarget.APPLY_TO_NO_REPOS)

        targets = WebHookTarget.objects.for_event('event1')
        self.assertEqual(targets, [target1, target2])

    def test_for_event_with_all_events(self):
        """Testing WebHookTargetManager.for_event with ALL_EVENTS"""
        with self.assertRaisesMessage(ValueError,
                                      '"*" is not a valid event choice'):
            WebHookTarget.objects.for_event(WebHookTarget.ALL_EVENTS)
