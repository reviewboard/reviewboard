"""Migration of legacy bug tracker settings to configurations.

This turns per-repository bug tracker state (the ``bug_tracker`` URL
template and ``bug_tracker_*``/``bug_tracker-*`` keys in ``extra_data``)
into :py:class:`~reviewboard.hostingsvcs.models.ConfiguredBugTracker` rows, and
assigns each repository's default bug tracker.

The legacy fields are never modified. They remain the compatibility
surface for older consumers.

Version Added:
    9.0
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import TYPE_CHECKING, TypedDict

from reviewboard.hostingsvcs.base import hosting_service_registry
from reviewboard.hostingsvcs.models import ConfiguredBugTracker
from reviewboard.scmtools.models import Repository

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from typelets.json import JSONDict


logger = logging.getLogger(__name__)


#: The extra_data key storing a migrated configuration's fingerprint.
#:
#: Version Added:
#:     9.0
FINGERPRINT_KEY = '__migrated_fingerprint'


#: The version of the deduplication fingerprint.
#:
#: Version Added:
#:     9.0
FINGERPRINT_VERSION = 1


# TODO: Switch to StrEnum once we're on Python 3.11+
class BugTrackerCase(str, Enum):
    """Classifications of a repository's legacy bug tracker configuration.

    Version Added:
        9.0
    """

    #: The repository uses its hosting service's tracker.
    IN_REPO = 'in-repo'

    #: The repository uses a standalone tracker service.
    SERVICE = 'service'

    #: The repository uses a custom bug URL.
    CUSTOM_URL = 'custom-url'


def classify_repository(
    repository: Repository,
) -> BugTrackerCase | None:
    """Classify a repository's legacy bug tracker configuration.

    Version Added:
        9.0

    Args:
        repository (reviewboard.scmtools.models.Repository):
            The repository to classify.

    Returns:
        BugTrackerCase:
        The classification, or ``None`` if the repository has no bug
        tracker configured.
    """
    extra_data = repository.extra_data or {}

    if extra_data.get('bug_tracker_use_hosting'):
        if repository.hosting_account_id is not None:
            return BugTrackerCase.IN_REPO
        else:
            return None

    if extra_data.get('bug_tracker_type'):
        return BugTrackerCase.SERVICE

    if repository.bug_tracker:
        # This covers both custom URLs with a %s placeholder and plain
        # URLs without one (which render bare bug IDs, as before).
        return BugTrackerCase.CUSTOM_URL

    return None


def get_settings_for_repository(
    repository: Repository,
    tracker_case: BugTrackerCase,
) -> JSONDict:
    """Return the configuration settings for a repository's tracker.

    Version Added:
        9.0

    Args:
        repository (reviewboard.scmtools.models.Repository):
            The repository being migrated.

        tracker_case (BugTrackerCase):
            The repository's classification.

    Returns:
        dict:
        The settings for the configuration.
    """
    extra_data = repository.extra_data or {}

    match tracker_case:
        case BugTrackerCase.IN_REPO:
            # Copy the hosting settings the service's bug tracker URL
            # template needs. These are inherently per-repository.
            tracker_settings = {
                key: value
                for key, value in extra_data.items()
                if not key.startswith(('bug_tracker', '__'))
            }

            account = repository.hosting_account
            tracker_settings['plan'] = extra_data.get('repository_plan') or ''

            if account is not None:
                tracker_settings['hosting_account_username'] = account.username
                tracker_settings['hosting_url'] = account.hosting_url

            return tracker_settings

        case BugTrackerCase.SERVICE:
            tracker_settings = {
                key.removeprefix('bug_tracker-'): value
                for key, value in extra_data.items()
                if key.startswith('bug_tracker-')
            }

            tracker_settings['plan'] = extra_data.get('bug_tracker_plan') or ''
            tracker_settings['hosting_url'] = \
                extra_data.get('bug_tracker_hosting_url')

            return tracker_settings

        case BugTrackerCase.CUSTOM_URL:
            return {
                'url_template': repository.bug_tracker,
            }

        case _:
            raise ValueError(f'Invalid bug tracker case {tracker_case!r}')


def get_service_name_for_repository(
    repository: Repository,
    tracker_case: BugTrackerCase,
) -> str | None:
    """Return the service name for a repository's tracker configuration.

    Version Added:
        9.0

    Args:
        repository (reviewboard.scmtools.models.Repository):
            The repository being migrated.

        tracker_case (BugTrackerCase):
            The repository's classification.

    Returns:
        str:
        The service name, or ``None`` if it could not be determined.
    """
    match tracker_case:
        case BugTrackerCase.IN_REPO:
            account = repository.hosting_account

            if account is not None:
                return account.service_name

            return None

        case BugTrackerCase.SERVICE:
            return (repository.extra_data or {}).get('bug_tracker_type')

        case BugTrackerCase.CUSTOM_URL:
            return 'custom-bug-tracker'

        case _:
            raise ValueError(f'Invalid bug tracker case {tracker_case!r}')


def make_fingerprint(
    repository: Repository,
    tracker_case: BugTrackerCase,
) -> str:
    """Return the deduplication fingerprint for a repository's tracker.

    Repositories with identical fingerprints share one configuration.
    Use-hosting configurations are never shared, since their settings
    are inherently per-repository.

    Version Added:
        9.0

    Args:
        repository (reviewboard.scmtools.models.Repository):
            The repository being migrated.

        tracker_case (BugTrackerCase):
            The repository's classification.

    Returns:
        str:
        The fingerprint, as a stable JSON string.
    """
    local_site_id = repository.local_site_id

    data: Any

    match tracker_case:
        case BugTrackerCase.IN_REPO:
            data = [tracker_case, repository.pk]

        case BugTrackerCase.SERVICE:
            tracker_settings = get_settings_for_repository(repository,
                                                           tracker_case)
            data = [
                tracker_case,
                get_service_name_for_repository(repository, tracker_case),
                local_site_id,
                sorted(
                    (key, str(value))
                    for key, value in tracker_settings.items()
                ),
            ]

        case BugTrackerCase.CUSTOM_URL:
            data = [tracker_case, repository.bug_tracker, local_site_id]

        case _:
            raise ValueError(f'Invalid bug tracker case {tracker_case!r}')

    return json.dumps([FINGERPRINT_VERSION, *data], sort_keys=True)


def _generate_name(
    repository: Repository,
    tracker_case: BugTrackerCase,
    service_name: str,
) -> str:
    """Return a display name for a new configuration.

    Version Added:
        9.0

    Args:
        repository (reviewboard.scmtools.models.Repository):
            The repository being migrated.

        tracker_case (BugTrackerCase):
            The repository's classification.

        service_name (str):
            The configuration's service name.

    Returns:
        str:
        The generated name, unique within the Local Site.
    """
    service_cls = hosting_service_registry.get_hosting_service(service_name)

    if service_cls is not None and service_cls.name:
        base_name = str(service_cls.name)
    else:
        base_name = service_name

    if tracker_case == BugTrackerCase.IN_REPO:
        base_name = f'{base_name} ({repository.name})'
    else:
        tracker_settings = get_settings_for_repository(repository,
                                                       tracker_case)
        # As of the date of this migration to the new bug tracker data model,
        # Splat is the only bug tracker implementation where multiple
        # configured trackers share the same hosting_url value and need to be
        # disambiguated by a different field.
        disambiguator = (tracker_settings.get('hosting_url') or
                         tracker_settings.get('splat_org_name'))

        if disambiguator:
            base_name = f'{base_name} ({disambiguator})'

    name = base_name
    i = 2

    while (ConfiguredBugTracker.objects
           .filter(name=name,
                   local_site=repository.local_site_id)
           .exists()):
        name = f'{base_name} ({i})'
        i += 1

    return name


def _load_configs_by_fingerprint(
    queryset: (Iterable[ConfiguredBugTracker] | None) = None,
) -> dict[str, ConfiguredBugTracker]:
    """Return existing migrated configurations, keyed by fingerprint.

    Version Added:
        9.0

    Args:
        queryset (iterable of reviewboard.hostingsvcs.models.
                  ConfiguredBugTracker, optional):
            The configurations to index. Defaults to all configurations.

    Returns:
        dict:
        A mapping of fingerprints to configurations.
    """
    if queryset is None:
        queryset = ConfiguredBugTracker.objects.all()

    configs_by_fingerprint: dict[str, ConfiguredBugTracker] = {}

    for config in queryset:
        fingerprint = (config.extra_data or {}).get(FINGERPRINT_KEY)

        if fingerprint:
            configs_by_fingerprint[fingerprint] = config

    return configs_by_fingerprint


class MaterializeConfigsStats(TypedDict):
    """Statistics on the migrated configs.

    Version Added:
        9.0
    """

    #: The number of created bug tracker configs.
    created: int

    #: The number of skipped repositories.
    skipped: int

    #: The number of updated bug tracker configs.
    updated: int


def materialize_configs(
    repositories: (Iterable[Repository] | None) = None,
) -> MaterializeConfigsStats:
    """Create bug tracker configurations for legacy repository settings.

    This is idempotent. Configurations are matched on their stored
    fingerprint before anything is created. A repository's default bug
    tracker is assigned when unset, and re-assigned when the current
    default was itself derived from legacy settings (so legacy writes
    keep it in sync). A manually-assigned default is never replaced.

    Version Added:
        9.0

    Args:
        repositories (iterable of reviewboard.scmtools.models.Repository,
                      optional):
            The repositories to migrate. Defaults to all repositories.

    Returns:
        MaterializeConfigsStats:
        Statistics on the migration.
    """
    if repositories is None:
        repositories = (
            Repository.objects.all()
            .select_related('hosting_account')
        )

    # Make sure the sentinel exists, so unattributed bugs always have a
    # tracker to point at.
    ConfiguredBugTracker.objects.get_sentinel()

    stats: MaterializeConfigsStats = {
        'created': 0,
        'skipped': 0,
        'updated': 0,
    }

    configs_by_fingerprint = _load_configs_by_fingerprint()

    # Load every existing configuration/repository link up front, so the
    # loop doesn't need a query per repository. New links are collected
    # and added in one shot at the end.
    RepositoriesThrough = \
        ConfiguredBugTracker.repositories.through  # noqa: N806
    linked: set[tuple[int, int]] = set(
        RepositoriesThrough.objects.values_list(
            'configuredbugtracker_id',
            'repository_id',
        )
    )
    new_links: set[tuple[int, int]] = set()

    for repository in repositories:
        tracker_case = classify_repository(repository)

        if tracker_case is None:
            continue

        service_name = get_service_name_for_repository(repository,
                                                       tracker_case)

        if not service_name:
            stats['skipped'] += 1
            continue

        fingerprint = make_fingerprint(repository, tracker_case)
        config = configs_by_fingerprint.get(fingerprint)

        if config is None:
            if tracker_case == BugTrackerCase.IN_REPO:
                hosting_account = repository.hosting_account
            else:
                hosting_account = None

            config = ConfiguredBugTracker.objects.create(
                name=_generate_name(repository, tracker_case, service_name),
                service_name=service_name,
                hosting_account=hosting_account,
                settings=get_settings_for_repository(repository, tracker_case),
                local_site_id=repository.local_site_id,
                apply_to=ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS,
                extra_data={
                    FINGERPRINT_KEY: fingerprint,
                })
            stats['created'] += 1

        configs_by_fingerprint[fingerprint] = config

        updated = False

        link = (config.pk, repository.pk)

        if link not in linked:
            linked.add(link)
            new_links.add(link)
            updated = True

        default_id = repository.default_bug_tracker_id

        if (default_id != config.pk and
            (default_id is None or
             FINGERPRINT_KEY in (
                repository.default_bug_tracker.extra_data or {}))):
            # Assign the default if it's unset. If the current default
            # was itself derived from legacy settings, follow the new
            # settings. A manually-assigned default is never replaced.
            repository.default_bug_tracker = config
            repository.save(update_fields=('default_bug_tracker',))
            updated = True

        if updated:
            stats['updated'] += 1
        else:
            stats['skipped'] += 1

    if new_links:
        RepositoriesThrough.objects.bulk_create(
            RepositoriesThrough(
                configuredbugtracker_id=config_id,
                repository_id=repository_id,
            )
            for config_id, repository_id in new_links
        )

    return stats


def sync_default_bug_tracker_from_url(
    repository: Repository,
) -> None:
    """Sync a repository's default bug tracker from its legacy URL.

    This runs when the legacy ``bug_tracker`` URL template is written
    directly. It gets or creates a matching custom configuration and
    assigns it as the default, so the two fields never diverge. An
    empty value clears the default.

    Hosting-based bug trackers are left alone here. They are synced
    after the save by :py:func:`sync_default_bug_tracker_from_hosting`,
    once the repository has an ID.

    Version Added:
        9.0

    Args:
        repository (reviewboard.scmtools.models.Repository):
            The repository being saved.
    """
    tracker_case = classify_repository(repository)

    if tracker_case is not None and tracker_case != BugTrackerCase.CUSTOM_URL:
        return

    if not repository.bug_tracker:
        if repository.default_bug_tracker_id is not None:
            repository.default_bug_tracker = None

        return

    fingerprint = make_fingerprint(repository, tracker_case)
    config = _load_configs_by_fingerprint(
        ConfiguredBugTracker.objects.filter(service_name='custom-bug-tracker')
    ).get(fingerprint)

    if config is None:
        config = ConfiguredBugTracker.objects.create(
            name=_generate_name(repository, tracker_case,
                                'custom-bug-tracker'),
            service_name='custom-bug-tracker',
            settings=get_settings_for_repository(repository, tracker_case),
            local_site_id=repository.local_site_id,
            apply_to=ConfiguredBugTracker.APPLY_TO_SELECTED_REPOS,
            extra_data={
                FINGERPRINT_KEY: fingerprint,
            })

    if repository.pk is None:
        # The repository hasn't been saved yet, so it can't be linked to
        # the configuration. Repository.save() finishes the link once
        # the repository has an ID.
        repository._bug_tracker_scope_pending = True
    else:
        config.repositories.add(repository)

    if repository.default_bug_tracker_id != config.pk:
        repository.default_bug_tracker = config


def sync_default_bug_tracker_from_hosting(
    repository: Repository,
) -> None:
    """Sync a repository's default bug tracker from legacy hosting settings.

    This runs after a repository is saved with hosting-based bug tracker
    settings in ``extra_data`` (``bug_tracker_use_hosting`` or
    ``bug_tracker_type``). It gets or creates the matching configuration
    and assigns it as the default, so a repository never has legacy
    hosting settings without a default bug tracker.

    A manually-assigned default is left alone. A default already derived
    from the same settings is a no-op.

    The repository must already be saved. Use-hosting configurations
    are scoped to the repository, so they need its ID.

    Version Added:
        9.0

    Args:
        repository (reviewboard.scmtools.models.Repository):
            The saved repository.
    """
    tracker_case = classify_repository(repository)

    if tracker_case is None or tracker_case == BugTrackerCase.CUSTOM_URL:
        return

    default = repository.default_bug_tracker

    if default is not None:
        fingerprint = (default.extra_data or {}).get(FINGERPRINT_KEY)

        if (fingerprint is None or
            fingerprint == make_fingerprint(repository, tracker_case)):
            return

    materialize_configs([repository])
