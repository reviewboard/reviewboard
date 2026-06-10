"""Test paginator for hosting services.

Version Added:
    9.0
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reviewboard.hostingsvcs.base.paginator import (
    BasePaginator,
    InvalidPageError,
    PageDataItemT,
    PageDataT,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


class TestPaginator(BasePaginator[PageDataItemT, PageDataT]):
    """Test paginator.

    Version Added:
        9.0
    """

    ######################
    # Instance variables #
    ######################

    #: The data for the pages.
    _pages: Sequence[PageDataT]

    #: The current page.
    _i: int

    def __init__(
        self,
        pages: Sequence[PageDataT],
    ) -> None:
        """Initialize the paginator.

        Args:
            pages (list):
                A list of page data to return.

        Raises:
            ValueError:
                The pages list was empty.
        """
        super().__init__()

        if len(pages) == 0:
            raise ValueError('Cannot create a TestPaginator with no data')

        self._pages = pages
        self._i = 0
        self.page_data = self._pages[0]

    @property
    def has_prev(self) -> bool:
        """Whether there's a previous page available."""
        return self._i > 0

    @property
    def has_next(self) -> bool:
        """Whether there's a next page available."""
        return self._i + 1 < len(self._pages)

    def prev(self) -> PageDataT | None:
        """Fetch the previous page, returning the page data.

        Returns:
            object:
            The resulting page data.

        Raises:
            reviewboard.hostingsvcs.base.paginator.InvalidPageError:
                There was no previous page.
        """
        if not self.has_prev:
            raise InvalidPageError

        self._i -= 1
        self.page_data = self._pages[self._i]

        return self.page_data

    def next(self) -> PageDataT | None:
        """Fetch the next page, returning the page data.

        Returns:
            object:
            The resulting page data.

        Raises:
            reviewboard.hostingsvcs.base.paginator.InvalidPageError:
                There was no next page.
        """
        if not self.has_next:
            raise InvalidPageError

        self._i += 1
        self.page_data = self._pages[self._i]

        return self.page_data
