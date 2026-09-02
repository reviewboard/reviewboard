"""Tests for reviewboard.hostingsvcs.bug_tracker_migration.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb
import pytest
from django.core.management import call_command

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
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
from reviewboard.scmtools.models import Repository
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    _MixinParent = TestCase
else:
    _MixinParent = object


#: Decorator to ignore deprecation warnings for legacy URLs.
#:
#: Several tests exercise the deprecated direct bug_tracker writes on
#: purpose. Silence the deprecation warning for those.
#:
#: Version Added:
#:     9.0
ignore_legacy_url_deprecation = pytest.mark.filterwarnings(
    'ignore::reviewboard.deprecation.RemovedInReviewBoard11_0Warning')


class LegacyRepositoryTestsMixin(kgb.SpyAgency, _MixinParent):
    """Mixin building repositories with unsynced legacy settings.

    These tests require starting with legacy repositories, created
    before bug tracker configurations existed. This stops
    :py:meth:`Repository.save()
    <reviewboard.scmtools.models.Repository.save>` from syncing
    configurations during setup, so the stored legacy state reaches the
    migration functions untouched.

    Version Added:
        9.0
    """

    def setUp(self) -> None:
        """Set up the test case."""
        super().setUp()

        self.spy_on(Repository._sync_bug_tracker_fields,
                    owner=Repository,
                    op=kgb.SpyOpReturn(set()))
        self.spy_on(Repository._sync_hosting_bug_tracker,
                    owner=Repository,
                    call_original=False)


class ClassifyRepositoryTests(LegacyRepositoryTestsMixin, TestCase):
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

    @ignore_legacy_url_deprecation
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

    @ignore_legacy_url_deprecation
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

    @ignore_legacy_url_deprecation
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

    @ignore_legacy_url_deprecation
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

    @ignore_legacy_url_deprecation
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


class RepositorySaveSyncTests(TestCase):
    """Unit tests for the bug_tracker write sync on Repository.save.

    Version Added:
        9.0
    """

    fixtures = ['test_scmtools']

    @ignore_legacy_url_deprecation
    def test_write_url_syncs_default(self) -> None:
        """Testing a direct bug_tracker write syncs the default
        tracker
        """
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s')

        repository.refresh_from_db()
        config = repository.default_bug_tracker
        self.assertIsNotNone(config)
        self.assertEqual(config.service_name, 'custom-bug-tracker')
        self.assertEqual(config.settings['url_template'],
                         'https://bugs.example.com/%s')

        # Clearing the URL clears the default.
        repository.bug_tracker = ''
        repository.save()

        repository.refresh_from_db()
        self.assertIsNone(repository.default_bug_tracker_id)

    @ignore_legacy_url_deprecation
    def test_new_repository_with_url_syncs_default(self) -> None:
        """Testing creating a new repository with a bug_tracker URL syncs
        the default tracker
        """
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s')

        repository.refresh_from_db()
        config = repository.default_bug_tracker
        self.assertIsNotNone(config)
        self.assertEqual(config.service_name, 'custom-bug-tracker')
        self.assertEqual(list(config.repositories.all()), [repository])

    def test_default_assignment_wins_over_url_write(self) -> None:
        """Testing an explicit default tracker assignment wins over a
        bug_tracker URL write in the same save
        """
        manual_config = ConfiguredBugTracker.objects.create(
            name='Manual Tracker',
            service_name='custom-bug-tracker',
            settings={
                'url_template': 'https://manual.example.com/%s',
            })

        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s',
            default_bug_tracker=manual_config)

        repository.refresh_from_db()
        self.assertEqual(repository.default_bug_tracker_id,
                         manual_config.pk)
        self.assertEqual(repository.bug_tracker,
                         'https://manual.example.com/%s')

    def test_default_regenerates_url(self) -> None:
        """Testing assigning a default tracker regenerates the legacy
        URL
        """
        config = ConfiguredBugTracker.objects.create(
            name='Tracker',
            service_name='custom-bug-tracker',
            settings={
                'url_template': 'https://bugs.example.com/%s',
            })

        repository = self.create_repository(
            default_bug_tracker=config)

        repository.refresh_from_db()
        self.assertEqual(repository.bug_tracker,
                         'https://bugs.example.com/%s')

    @ignore_legacy_url_deprecation
    def test_unrelated_save_preserves_url(self) -> None:
        """Testing a save touching neither bug tracker field leaves the
        legacy URL alone
        """
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s')

        # Write the legacy URL without going through the sync, standing in
        # for any consumer that composes the URL itself.
        Repository.objects.filter(pk=repository.pk).update(
            bug_tracker='https://other.example.com/%s')

        repository.refresh_from_db()
        repository.name = 'New Name'
        repository.save()

        repository.refresh_from_db()
        self.assertEqual(repository.bug_tracker,
                         'https://other.example.com/%s')

    def test_use_hosting_syncs_default(self) -> None:
        """Testing saving legacy use-hosting settings syncs the default
        tracker
        """
        account = HostingServiceAccount.objects.create(
            service_name='github',
            username='test-user')
        repository = self.create_repository(
            hosting_account=account,
            extra_data={
                'bug_tracker_use_hosting': True,
                'repository_plan': 'public',
                'github_public_repo_name': 'myrepo',
            })

        repository.refresh_from_db()
        config = repository.default_bug_tracker
        self.assertIsNotNone(config)
        self.assertEqual(config.service_name, 'github')
        self.assertEqual(config.hosting_account_id, account.pk)
        self.assertEqual(list(config.repositories.all()), [repository])
        self.assertEqual(repository.bug_tracker,
                         'http://github.com/test-user/myrepo/issues#issue/%s')

        # Saving again with the same settings is a no-op.
        repository.name = 'New Name'
        repository.save()

        repository.refresh_from_db()
        self.assertEqual(repository.default_bug_tracker_id, config.pk)
        self.assertEqual(ConfiguredBugTracker.objects.count(), 2)

    def test_service_syncs_default(self) -> None:
        """Testing saving legacy standalone service settings syncs the
        default tracker
        """
        repository = self.create_repository(extra_data={
            'bug_tracker_type': 'splat',
            'bug_tracker-splat_org_name': 'my-org',
        })

        repository.refresh_from_db()
        config = repository.default_bug_tracker
        self.assertIsNotNone(config)
        self.assertEqual(config.service_name, 'splat')
        self.assertEqual(config.settings['splat_org_name'], 'my-org')
        self.assertEqual(list(config.repositories.all()), [repository])

    def test_unrelated_update_fields_skip_hosting_sync(self) -> None:
        """Testing a save limited to unrelated fields skips the hosting
        tracker sync
        """
        repository = self.create_repository()

        # Write the legacy settings without going through the sync.
        Repository.objects.filter(pk=repository.pk).update(extra_data={
            'bug_tracker_type': 'splat',
            'bug_tracker-splat_org_name': 'my-org',
        })

        repository.refresh_from_db()
        repository.name = 'New Name'
        repository.save(update_fields=('name',))

        repository.refresh_from_db()
        self.assertIsNone(repository.default_bug_tracker_id)

    @ignore_legacy_url_deprecation
    def test_switch_to_service_replaces_derived_default(self) -> None:
        """Testing switching the legacy fields to a hosting service replaces
        a derived default tracker
        """
        repository = self.create_repository(
            bug_tracker='https://bugs.example.com/%s')

        repository.refresh_from_db()
        old_config = repository.default_bug_tracker
        self.assertIsNotNone(old_config)

        repository.extra_data.update({
            'bug_tracker_type': 'github',
            'bug_tracker_plan': 'public-org',
            'bug_tracker-github_public_org_name': 'myorg',
            'bug_tracker-github_public_org_repo_name': 'myrepo',
        })
        repository.bug_tracker = \
            'http://github.com/myorg/myrepo/issues#issue/%s'
        repository.save()

        repository.refresh_from_db()
        config = repository.default_bug_tracker
        self.assertIsNotNone(config)
        self.assertNotEqual(config.pk, old_config.pk)
        self.assertEqual(config.service_name, 'github')
        self.assertEqual(config.settings['github_public_org_name'], 'myorg')
        self.assertEqual(repository.bug_tracker,
                         'http://github.com/myorg/myrepo/issues#issue/%s')

    @ignore_legacy_url_deprecation
    def test_switch_to_service_keeps_manual_default(self) -> None:
        """Testing switching the legacy fields to a hosting service keeps a
        manually-assigned default tracker
        """
        manual_config = ConfiguredBugTracker.objects.create(
            name='Manual Tracker',
            service_name='custom-bug-tracker',
            settings={
                'url_template': 'https://manual.example.com/%s',
            })

        repository = self.create_repository(
            default_bug_tracker=manual_config)

        repository.extra_data['bug_tracker_type'] = 'github'
        repository.bug_tracker = \
            'http://github.com/myorg/myrepo/issues#issue/%s'
        repository.save()

        repository.refresh_from_db()
        self.assertEqual(repository.default_bug_tracker_id, manual_config.pk)

    def test_suppress_deprecation_flag(self) -> None:
        """Testing the deprecation suppression flag skips the warning for
        one save and still syncs the default tracker
        """
        repository = self.create_repository()

        repository._suppress_bug_tracker_deprecation = True
        repository.bug_tracker = 'https://bugs.example.com/%s'

        with self.assertNoWarnings():
            repository.save()

        repository.refresh_from_db()
        self.assertIsNotNone(repository.default_bug_tracker_id)

        # The flag only covers the save it was set for.
        repository.bug_tracker = 'https://other.example.com/%s'

        with self.assertWarns(RemovedInReviewBoard11_0Warning):
            repository.save()
