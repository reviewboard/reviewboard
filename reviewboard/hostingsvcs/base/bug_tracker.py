"""An interface to a bug tracker.

Version Changed:
    8.0:
    Renamed this module from ``reviewboard.hostingsvcs.bugtracker``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from django.utils.translation import gettext_lazy as _
from djblets.cache.backend import cache_memoize

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import ClassVar, Literal

    from typelets.django.strings import StrOrPromise
    from typing_extensions import NotRequired

    from reviewboard.scmtools.models import Repository


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

    Version Changed:
        9.0:
        Added :py:attr:`bug_tracker_label` and :py:attr:`bugs_in_repo`.

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

    def get_bug_info(
        self,
        repository: Repository,
        bug_id: str,
    ) -> BugInfo:
        """Return the information for the specified bug.

        This should return a :py:class:`BugInfo` dictionary.

        This is cached for 60 seconds to reduce the number of queries to the
        bug trackers and make things seem fast after the first infobox load,
        but is still a short enough time to give relatively fresh data.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            bug_id (str):
                The ID of the bug to fetch.

        Returns:
            BugInfo:
            Information about the bug.
        """
        return cache_memoize(self.make_bug_cache_key(repository, bug_id),
                             lambda: self.get_bug_info_uncached(repository,
                                                                bug_id),
                             expiration=60)

    def get_bug_info_uncached(
        self,
        repository: Repository,
        bug_id: str,
    ) -> BugInfo:
        """Return the information for the specified bug.

        This should be implemented by subclasses.

        Args:
            repository (reviewboard.scmtools.models.Repository):
                The repository object.

            bug_id (str):
                The ID of the bug to fetch.

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
