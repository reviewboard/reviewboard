"""Tests for reviewboard.hostingsvcs.bug_tracker_migration.

Version Added:
    9.0
"""

from __future__ import annotations

import pytest
from django.core.management import call_command

from reviewboard.hostingsvcs.bug_tracker_migration import (
    BugTrackerCase,
    classify_repository,
    materialize_configs,
)
from reviewboard.hostingsvcs.models import (
    ConfiguredBugTracker,
    HostingServiceAccount,
    SENTINEL_BUG_TRACKER_SERVICE_NAME,
)
from reviewboard.reviews.models.bug import BUGS_MIGRATED_KEY
from reviewboard.testing import TestCase


#: Decorator to ignore deprecation warnings for legacy URLs.
#:
#: Several tests exercise the deprecated direct bug_tracker writes on
#: purpose. Silence the deprecation warning for those.
#:
#: Version Added:
#:     9.0
ignore_legacy_url_deprecation = pytest.mark.filterwarnings(
    'ignore::reviewboard.deprecation.RemovedInReviewBoard11_0Warning')


class ClassifyRepositoryTests(TestCase):
    """Unit tests for classify_repository.

    Version Added:
        9.0
    """

    fixtures = ['test_scmtools']

    def test_use_hosting(self) -> None:
        """Testing classify_repository with use-hosting settings"""
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='test-user')
        repository = self.create_repository(
            hosting_account=account,
            extra_data={
                'bug_tracker_use_hosting': True,
            })

        self.assertEqual(classify_repository(repository),
                         BugTrackerCase.IN_REPO)

    def test_service(self) -> None:
        """Testing classify_repository with a standalone tracker service"""
        repository = self.create_repository(extra_data={
            'bug_tracker_type': 'splat',
            'bug_tracker-splat_org_name': 'my-org',
        })

        self.assertEqual(classify_repository(repository),
                         BugTrackerCase.SERVICE)

    def test_custom_url(self) -> None:
        """Testing classify_repository with a custom URL"""
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s')

        self.assertEqual(classify_repository(repository),
                         BugTrackerCase.CUSTOM_URL)

        # URLs without a placeholder classify the same way. They render
        # bare bug IDs, as before.
        repository = self.create_repository(
            name='other',
            bug_tracker='https://bugs.example.com/')

        self.assertEqual(classify_repository(repository),
                         BugTrackerCase.CUSTOM_URL)

    def test_no_bug_tracker(self) -> None:
        """Testing classify_repository without bug tracker settings"""
        repository = self.create_repository()

        self.assertIsNone(classify_repository(repository))


class MaterializeConfigsTests(TestCase):
    """Unit tests for materialize_configs.

    Version Added:
        9.0
    """

    fixtures = ['test_scmtools']

    def test_service_configs_deduplicated(self) -> None:
        """Testing materialize_configs deduplicates identical service
        settings
        """
        extra_data = {
            'bug_tracker_type': 'splat',
            'bug_tracker-splat_org_name': 'my-org',
        }
        repository1 = self.create_repository(name='repo1',
                                             extra_data=dict(extra_data))
        repository2 = self.create_repository(name='repo2',
                                             extra_data=dict(extra_data))
        repository3 = self.create_repository(
            name='repo3',
            extra_data={
                'bug_tracker_type': 'splat',
                'bug_tracker-splat_org_name': 'other-org',
            })

        materialize_configs()

        configs = list(
            ConfiguredBugTracker.objects
            .filter(service_name='splat')
            .order_by('pk')
        )
        self.assertEqual(len(configs), 2)

        config = configs[0]

        # The prefix is stripped from the settings.
        self.assertEqual(config.settings['splat_org_name'], 'my-org')
        self.assertNotIn('bug_tracker-splat_org_name', config.settings)

        self.assertEqual(config.apply_to,
                         ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS)
        self.assertEqual(
            set(config.repositories.values_list('pk', flat=True)),
            {repository1.pk, repository2.pk})

        for repository in (repository1, repository2):
            repository.refresh_from_db()
            self.assertEqual(repository.default_bug_tracker_id, config.pk)

        repository3.refresh_from_db()
        self.assertEqual(repository3.default_bug_tracker_id, configs[1].pk)

    def test_use_hosting_configs_not_deduplicated(self) -> None:
        """Testing materialize_configs keeps in-repo configs
        per-repository
        """
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='test-user')

        for name in ('repo1', 'repo2'):
            self.create_repository(
                name=name,
                hosting_account=account,
                extra_data={
                    'bug_tracker_use_hosting': True,
                    'repository_plan': 'public',
                    'github_public_repo_name': name,
                })

        materialize_configs()

        configs = list(
            ConfiguredBugTracker.objects.filter(service_name='github'))
        self.assertEqual(len(configs), 2)

        for config in configs:
            self.assertEqual(config.hosting_account_id, account.pk)
            self.assertEqual(config.repositories.count(), 1)

    def test_custom_url_configs(self) -> None:
        """Testing materialize_configs with custom URLs"""
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s')

        materialize_configs()

        repository.refresh_from_db()
        config = repository.default_bug_tracker
        self.assertIsNotNone(config)
        self.assertEqual(config.service_name, 'custom-bug-tracker')
        self.assertEqual(config.settings['url_template'],
                         'https://bugs.example.com/%s')
        self.assertEqual(config.get_bug_url('123'),
                         'https://bugs.example.com/123')

    def test_local_site_isolation(self) -> None:
        """Testing materialize_configs never shares configs across
        Local Sites
        """
        local_site = self.create_local_site()

        self.create_repository(
            name='repo1',
            bug_tracker='https://bugs.example.com/%s')
        self.create_repository(
            name='repo2',
            local_site=local_site,
            bug_tracker='https://bugs.example.com/%s')

        materialize_configs()

        configs = ConfiguredBugTracker.objects.filter(
            service_name='custom-bug-tracker')
        self.assertEqual(configs.count(), 2)
        self.assertEqual(
            {
                config.local_site_id
                for config in configs
            },
            {
                None,
                local_site.pk,
            })

    def test_idempotent(self) -> None:
        """Testing materialize_configs is idempotent"""
        self.create_repository(
            bug_tracker='https://bugs.example.com/%s')

        materialize_configs()
        count = ConfiguredBugTracker.objects.count()

        stats = materialize_configs()
        self.assertEqual(ConfiguredBugTracker.objects.count(), count)
        self.assertEqual(stats['created'], 0)

    def test_never_overwrites_manual_default(self) -> None:
        """Testing materialize_configs never overwrites an assigned
        default bug tracker
        """
        manual_config = ConfiguredBugTracker.objects.create(
            name='Manual Tracker',
            service_name='splat')
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s',
            default_bug_tracker=manual_config)

        materialize_configs()

        repository.refresh_from_db()
        self.assertEqual(repository.default_bug_tracker_id,
                         manual_config.pk)

    def test_name_collisions(self) -> None:
        """Testing materialize_configs disambiguates colliding names"""
        self.create_repository(
            name='repo1',
            bug_tracker='https://bugs1.example.com/%s')
        self.create_repository(
            name='repo2',
            bug_tracker='https://bugs2.example.com/%s')

        materialize_configs()

        names = sorted(
            ConfiguredBugTracker.objects
            .filter(service_name='custom-bug-tracker')
            .values_list('name', flat=True)
        )
        self.assertEqual(names,
                         ['Custom Bug Tracker', 'Custom Bug Tracker (2)'])

    def test_creates_sentinel(self) -> None:
        """Testing materialize_configs creates the sentinel tracker"""
        materialize_configs()

        self.assertTrue(
            ConfiguredBugTracker.objects
            .filter(service_name=SENTINEL_BUG_TRACKER_SERVICE_NAME)
            .exists())


class BackfillBugsTests(TestCase):
    """Unit tests for the --backfill-bugs command option.

    Version Added:
        9.0
    """

    fixtures = ['test_users', 'test_scmtools']

    @ignore_legacy_url_deprecation
    def test_backfill(self) -> None:
        """Testing migrate-bug-trackers --backfill-bugs"""
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s')
        review_request = self.create_review_request(repository=repository,
                                                    publish=True)
        review_request.bugs_closed = '4,2'
        review_request.save(update_fields=('bugs_closed',))

        call_command('migrate-bug-trackers', backfill_bugs=True)

        review_request.refresh_from_db()
        self.assertTrue(review_request.extra_data.get(BUGS_MIGRATED_KEY))
        self.assertEqual(
            sorted(review_request.bugs.values_list('bug_id', flat=True)),
            ['2', '4'])
        self.assertEqual(review_request.get_bug_list(), ['2', '4'])

        # The bugs are attributed to the repository's new default tracker.
        review_request.repository.refresh_from_db()
        default_pk = review_request.repository.default_bug_tracker_id
        self.assertIsNotNone(default_pk)
        self.assertEqual(
            set(review_request.bugs.values_list('bug_tracker', flat=True)),
            {default_pk})

        # The stored string froze in place.
        self.assertEqual(review_request.bugs_closed, '4,2')

    def test_backfill_syncs_stale_links(self) -> None:
        """Testing --backfill-bugs re-syncs rows after legacy edits"""
        review_request = self.create_review_request(publish=True)
        review_request.bugs_closed = '1,2'
        review_request.save(update_fields=('bugs_closed',))

        call_command('migrate-bug-trackers', backfill_bugs=True)

        review_request.refresh_from_db()
        self.assertEqual(review_request.get_bug_list(), ['1', '2'])

        # Simulate a legacy edit that popped the marker, reverting the
        # row to string-driven behavior.
        review_request.bugs_closed = '3'
        review_request.extra_data.pop(BUGS_MIGRATED_KEY, None)
        review_request.save(update_fields=('bugs_closed', 'extra_data'))

        call_command('migrate-bug-trackers', backfill_bugs=True)

        review_request.refresh_from_db()

        # Materialization is a true sync: stale links are removed, not
        # just added to.
        self.assertEqual(
            list(review_request.bugs.values_list('bug_id', flat=True)),
            ['3'])
        self.assertEqual(review_request.get_bug_list(), ['3'])
