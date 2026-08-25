"""Tests for reviewboard.hostingsvcs.base.bug_tracker.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import kgb

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning
from reviewboard.hostingsvcs.base.bug_tracker import BaseBugTracker
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.testing import TestCase

if TYPE_CHECKING:
    from reviewboard.hostingsvcs.base.bug_tracker import BugInfo
    from reviewboard.scmtools.models import Repository


class _LegacyBugTracker(BaseBugTracker):
    """A bug tracker overriding the legacy signature."""

    def get_bug_info_uncached(
        self,
        repository: Repository,
        bug_id: str,
    ) -> BugInfo:
        return {
            'summary': f'Legacy bug {bug_id}',
            'description': 'From the legacy signature.',
            'status': 'open',
        }


class _ModernBugTracker(BaseBugTracker):
    """A bug tracker overriding the config-based signature."""

    supports_bug_info = True

    def get_bug_info_uncached(
        self,
        *,
        config: (ConfiguredBugTracker | None) = None,
        bug_id: str,
        repository: (Repository | None) = None,
    ) -> BugInfo:
        if config is not None:
            source = f'config:{config.pk}'
        elif repository is not None:
            source = f'repository:{repository.pk}'
        else:
            source = 'none'

        return {
            'summary': f'Bug {bug_id}',
            'description': f'From {source}.',
            'status': 'open',
        }


class BaseBugTrackerDispatchTests(kgb.SpyAgency, TestCase):
    """Unit tests for the BaseBugTracker signature dispatch.

    Version Added:
        9.0
    """

    fixtures = ['test_scmtools']  # noqa: RUF012

    def test_legacy_override_with_repository(self) -> None:
        """Testing get_bug_info with a legacy override and a repository"""
        repository = self.create_repository()
        tracker = _LegacyBugTracker()

        with self.assertWarns(RemovedInReviewBoard11_0Warning):
            info = tracker.get_bug_info(repository=repository, bug_id='123')

        self.assertEqual(info['summary'], 'Legacy bug 123')

    def test_legacy_override_with_config(self) -> None:
        """Testing get_bug_info with a legacy override and a config returns
        no info
        """
        config = ConfiguredBugTracker.objects.create(name='Tracker',
                                                     service_name='splat')
        tracker = _LegacyBugTracker()

        with self.assertWarns(RemovedInReviewBoard11_0Warning):
            info = tracker.get_bug_info(config=config, bug_id='123')

        self.assertEqual(info, {
            'summary': '',
            'description': '',
            'status': '',
        })

    def test_modern_override_with_config(self) -> None:
        """Testing get_bug_info with a modern override and a config"""
        config = ConfiguredBugTracker.objects.create(name='Tracker',
                                                     service_name='splat')
        tracker = _ModernBugTracker()

        info = tracker.get_bug_info(config=config, bug_id='123')

        self.assertEqual(info['description'], f'From config:{config.pk}.')

    def test_modern_override_with_repository(self) -> None:
        """Testing get_bug_info with a modern override and a repository"""
        repository = self.create_repository()
        tracker = _ModernBugTracker()

        info = tracker.get_bug_info(repository=repository, bug_id='123')

        self.assertEqual(info['description'],
                         f'From repository:{repository.pk}.')

    def test_modern_override_with_repository_and_default_config(self) -> None:
        """Testing get_bug_info with a modern override resolves the
        repository's default bug tracker
        """
        config = ConfiguredBugTracker.objects.create(name='Tracker',
                                                     service_name='splat')
        repository = self.create_repository()
        repository.default_bug_tracker = config
        repository.save(update_fields=('default_bug_tracker',))

        tracker = _ModernBugTracker()

        info = tracker.get_bug_info(repository=repository, bug_id='123')

        self.assertEqual(info['description'], f'From config:{config.pk}.')

    def test_cache_key_with_config(self) -> None:
        """Testing get_bug_info uses the config cache key"""
        config = ConfiguredBugTracker.objects.create(name='Tracker',
                                                     service_name='splat')
        tracker = _ModernBugTracker()

        self.spy_on(tracker.make_bug_cache_key_for_config)
        self.spy_on(tracker.make_bug_cache_key)

        tracker.get_bug_info(config=config, bug_id='123')

        self.assertSpyCalledWith(tracker.make_bug_cache_key_for_config,
                                 config, '123')
        self.assertSpyNotCalled(tracker.make_bug_cache_key)
        self.assertEqual(
            tracker.make_bug_cache_key_for_config(config, '123'),
            ['bug-tracker', str(config.pk), 'bug', '123'])

    def test_cache_key_with_repository(self) -> None:
        """Testing get_bug_info uses the legacy cache key without a config"""
        repository = self.create_repository()
        tracker = _ModernBugTracker()

        self.spy_on(tracker.make_bug_cache_key)
        self.spy_on(tracker.make_bug_cache_key_for_config)

        tracker.get_bug_info(repository=repository, bug_id='123')

        self.assertSpyCalledWith(tracker.make_bug_cache_key,
                                 repository, '123')
        self.assertSpyNotCalled(tracker.make_bug_cache_key_for_config)
        self.assertEqual(
            tracker.make_bug_cache_key(repository, '123'),
            ['repository', str(repository.pk), 'bug', '123'])
