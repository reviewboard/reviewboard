"""An interface to a bug tracker.

Version Changed:
    7.1:
    Renamed this module from ``reviewboard.hostingsvcs.bugtracker``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from djblets.cache.backend import cache_memoize

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import ClassVar, Literal

    from typing_extensions import NotRequired

    from reviewboard.scmtools.models import Repository


class BugInfo(TypedDict):
    """Information about a bug.

    Version Added:
        7.1
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
        7.1:
        Moved and renamed from
        ``reviewboard.hostingsvcs.bugtracker.BugTracker``.
    """

    #: The name of the bug tracker
    name: ClassVar[str | None] = None

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
            7.1:
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
