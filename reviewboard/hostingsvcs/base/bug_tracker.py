"""An interface to a bug tracker.

Version Changed:
    9.0:
    Reworked the bug info methods around
    :py:class:`~reviewboard.hostingsvcs.models.ConfiguredBugTracker`
    configurations.

Version Changed:
    8.0:
    Renamed this module from ``reviewboard.hostingsvcs.bugtracker``.
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, TypedDict

from django.utils.translation import gettext_lazy as _
from djblets.cache.backend import cache_memoize
from housekeeping import deprecate_non_keyword_only_args

from reviewboard.deprecation import RemovedInReviewBoard11_0Warning

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import ClassVar, Literal

    from typelets.django.strings import StrOrPromise
    from typing_extensions import NotRequired

    from reviewboard.hostingsvcs.models import ConfiguredBugTracker
    from reviewboard.scmtools.models import Repository


logger = logging.getLogger(__name__)


#: Cached signature styles for get_bug_info_uncached overrides.
_bug_info_style_cache: dict[type, bool] = {}


class BugInfo(TypedDict):
    """Information about a bug.

    Version Added:
        8.0
    """

    #: The description of the bug.
    description: str

    #: The text format of the description.
    description_text_format: NotRequired[Literal['html', 'markdown', 'plain']]

    #: A one-line summary of the bug.
    summary: str

    #: The bug's status.
    status: str


class BaseBugTracker:
    """An interface to a bug tracker.

    Bug tracker subclasses are used to enable interaction with different
    bug trackers.

    Subclasses should implement :py:meth:`get_bug_info_uncached` with the
    ``config``-based keyword signature. During the deprecation period,
    overrides using the legacy ``(repository, bug_id)`` signature keep
    working for repository-based calls, but are treated as having no bug
    info support when called with only a
    :py:class:`~reviewboard.hostingsvcs.models.ConfiguredBugTracker`
    configuration.

    Version Changed:
        9.0:
        * Added :py:attr:`bug_tracker_label` and :py:attr:`bugs_in_repo`.
        * Reworked the info methods around bug tracker configurations.

    Version Changed:
        8.0:
        Moved and renamed from
        ``reviewboard.hostingsvcs.bugtracker.BugTracker``.
    """

    #: The name of the bug tracker
    name: ClassVar[str | None] = None

    #: The default label for review request fields and UI.
    #:
    #: This can be overridden per-configuration through
    #: :py:attr:`ConfiguredBugTracker.name
    #: <reviewboard.hostingsvcs.models.ConfiguredBugTracker.name>`.
    #:
    #: Version Added:
    #:     9.0
    bug_tracker_label: ClassVar[StrOrPromise] = _('Bugs')

    #: Whether the bug tracker operates in-repo.
    #:
    #: In-repo bug trackers (such as GitHub or Forgejo issues) are tied
    #: to a repository on the hosting service. They are configured inside
    #: the repository configuration, not through Connected Services.
    #:
    #: Version Added:
    #:     9.0
    bugs_in_repo: ClassVar[bool] = False

    @deprecate_non_keyword_only_args(RemovedInReviewBoard11_0Warning)
    def get_bug_info(
        self,
        *,
        repository: (Repository | None) = None,
        bug_id: str,
        config: (ConfiguredBugTracker | None) = None,
    ) -> BugInfo:
        """Return the information for the specified bug.

        This should return a :py:class:`BugInfo` dictionary.

        This is cached for 60 seconds to reduce the number of queries to the
        bug trackers and make things seem fast after the first infobox load,
        but is still a short enough time to give relatively fresh data.

        Callers should pass ``config`` (and ``bug_id``) as keyword
        arguments. The positional ``repository`` form is deprecated. When
        only a repository is given, the repository's default bug tracker
        configuration is used when available.

        Version Changed:
            9.0:
            - Added the ``config`` argument.
            - Made arguments keyword-only.
            - Made ``repository`` optional.

        Args:
            repository (reviewboard.scmtools.models.Repository, optional):
                The repository object, for legacy calls.

            bug_id (str):
                The ID of the bug to fetch.

            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker,
                    optional):
                The bug tracker configuration.

                Version Added:
                    9.0

        Returns:
            BugInfo:
            Information about the bug.
        """
        if config is None and repository is not None:
            config = repository.get_default_bug_tracker()

        if self._uses_legacy_bug_info_signature():
            RemovedInReviewBoard11_0Warning.warn(
                f'{type(self).__name__}.get_bug_info_uncached() does '
                f'not include a config argument. This will be required in '
                f'Review Board 11.'
            )

            if repository is not None:
                # Legacy repository-based call into a legacy override.
                # This path is byte-identical to Review Board 8.
                return cache_memoize(
                    self.make_bug_cache_key(repository, bug_id),
                    lambda: self.get_bug_info_uncached(repository, bug_id),
                    expiration=60)
            else:
                # A configuration-only call cannot be dispatched to a
                # legacy override. Never fabricate a repository. The
                # caller gets no info.
                return {
                    'summary': '',
                    'description': '',
                    'status': '',
                }

        if config is not None and config.pk is not None:
            cache_key = self.make_bug_cache_key_for_config(config, bug_id)
        elif repository is not None:
            cache_key = self.make_bug_cache_key(repository, bug_id)
        else:
            cache_key = None

        if cache_key is None:
            return self.get_bug_info_uncached(bug_id=bug_id,
                                              config=config,
                                              repository=repository)

        return cache_memoize(
            cache_key,
            lambda: self.get_bug_info_uncached(bug_id=bug_id,
                                               config=config,
                                               repository=repository),
            expiration=60)

    @deprecate_non_keyword_only_args(RemovedInReviewBoard11_0Warning)
    def get_bug_info_uncached(
        self,
        *,
        repository: (Repository | None) = None,
        bug_id: str,
        config: (ConfiguredBugTracker | None) = None,
    ) -> BugInfo:
        """Return the information for the specified bug.

        This should be implemented by subclasses using the keyword-only
        signature. Implementations should read settings and credentials from
        ``config``. The ``repository`` argument is only provided for legacy
        repository-based calls, where no configuration may exist yet.

        Version Changed:
            9.0:
            - Made arguments keyword-only.
            - Added the ``config`` argument.

        Args:
            repository (reviewboard.scmtools.models.Repository, optional):
                The repository object, for legacy calls.

            bug_id (str):
                The ID of the bug to fetch.

            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker,
                    optional):
                The bug tracker configuration.

                Version Added:
                    9.0

        Returns:
            BugInfo:
            Information about the bug.
        """
        return {
            'summary': '',
            'description': '',
            'status': '',
        }

    def make_bug_cache_key(
        self,
        repository: Repository,
        bug_id: str,
    ) -> str | Sequence[str]:
        """Return a key to use when caching fetched bug information.

        This is the legacy repository-based cache key. Configuration
        -based calls use :py:meth:`make_bug_cache_key_for_config`.

        Version Changed:
            8.0:
            Changed to return a list of strings for the cache key, which
            :py:func:`djblets.cache.backend.cache_memoize` will use to create a
            safely escaped cache key.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            bug_id (str):
                The ID of the bug.

        Returns:
            list of str:
            A key to use for the cache.
        """
        return [
            'repository',
            str(repository.pk),
            'bug',
            bug_id,
        ]

    def make_bug_cache_key_for_config(
        self,
        config: ConfiguredBugTracker,
        bug_id: str,
    ) -> Sequence[str]:
        """Return a cache key for bug information on a configuration.

        Version Added:
            9.0

        Args:
            config (reviewboard.hostingsvcs.models.ConfiguredBugTracker):
                The bug tracker configuration.

            bug_id (str):
                The ID of the bug.

        Returns:
            list of str:
            A key to use for the cache.
        """
        return [
            'bug-tracker',
            str(config.pk),
            'bug',
            bug_id,
        ]

    def _uses_legacy_bug_info_signature(self) -> bool:
        """Return whether get_bug_info_uncached uses the legacy signature.

        Legacy overrides take ``(repository, bug_id)`` and have no
        ``config`` argument.

        Returns:
            bool:
            ``True`` if the subclass overrides
            :py:meth:`get_bug_info_uncached` with the legacy signature.
        """
        cls = type(self)

        try:
            return _bug_info_style_cache[cls]
        except KeyError:
            pass

        try:
            sig = inspect.signature(cls.get_bug_info_uncached)
            legacy = 'config' not in sig.parameters
        except (TypeError, ValueError):
            legacy = False

        _bug_info_style_cache[cls] = legacy

        return legacy
