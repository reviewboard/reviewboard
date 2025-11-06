"""Paginators for iterating over API results.

Version Added:
    6.0:
    This replaces the paginator code in the old
    :py:mod:`reviewboard.hostingsvcs.utils.paginator` module.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Callable, Generic, TYPE_CHECKING, TypeVar, Union

from housekeeping import deprecate_non_keyword_only_args
from typing_extensions import NotRequired, TypeAlias, TypedDict

from reviewboard.deprecation import RemovedInReviewBoard90Warning

if TYPE_CHECKING:
    from collections.abc import Iterator

    from typelets.funcs import KwargsDict

    from reviewboard.hostingsvcs.base import HostingServiceClient
    from reviewboard.hostingsvcs.base.http import HTTPHeaders, QueryArgs


_PageDataItemT = TypeVar('_PageDataItemT')
_PageDataT = TypeVar('_PageDataT')


#: Type alias for a normalize function for ProxyPaginator.
#:
#: Version Added:
#:     6.0
_ProxyNormalizePageDataFunc: TypeAlias = Callable[[Any],
                                                  Union[_PageDataT, None]]


class APIPaginatorPageData(TypedDict):
    """Data that can be returned from an APIPaginator.

    Version Added:
        6.0
    """

    #: The data from the page (generally as a list).
    #:
    #: Type:
    #:     object
    data: NotRequired[Any]

    #: The HTTP headers from the page response.
    #:
    #: Type:
    #:     dict
    headers: NotRequired[HTTPHeaders]

    #: The optional URL to the next page.
    #:
    #: Type:
    #:     str
    next_url: NotRequired[str | None]

    #: The optional limit on the number of items fetched on each page.
    #:
    #: Type:
    #:     int
    per_page: NotRequired[int | None]

    #: The optional URL to the previous page.
    #:
    #: Type:
    #:     str
    prev_url: NotRequired[str | None]

    #: The API response data.
    #:
    #: Type:
    #:     object
    response: NotRequired[object]

    #: The optional total number of items across all pages.
    #:
    #: Type:
    #:     int
    total_count: NotRequired[int | None]


class InvalidPageError(Exception):
    """An error representing an invalid page access.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.utils.paginator` to
          :py:mod:`reviewboard.hostingsvcs.base.paginator`.
    """


class BasePaginator(Generic[_PageDataItemT, _PageDataT]):
    """Base class for a paginator used in the hosting services code.

    This provides the basic state and stubbed functions for a simple
    paginator. Subclasses can build upon this to offer more advanced
    functionality.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.utils.paginator` to
          :py:mod:`reviewboard.hostingsvcs.base.paginator`.

        * This is now a generic, supporting typing for page data and items.
    """

    ######################
    # Instance variables #
    ######################

    #: The data for the current page.
    #:
    #: This is implementation-dependent, but will usually be a list. It must
    #: operate as a sequence of some kind.
    #:
    #: Type:
    #:     object
    page_data: _PageDataT | None

    #: The number of items to fetch per page.
    #:
    #: Type:
    #:     int
    per_page: int | None

    #: Keyword arguments to pass when making HTTP requests.
    #:
    #: Type:
    #:     dict
    request_kwargs: KwargsDict

    #: The starting page.
    #:
    #: Whether this is 0-based or 1-based depends on the hosting service.
    #:
    #: Type:
    #:     int
    start: int | None

    #: The total number of results across all pages.
    #:
    #: This will be ``None`` if the value isn't known.
    #:
    #: Type:
    #:     int
    total_count: int | None

    @deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
    def __init__(
        self,
        *,
        start: (int | None) = None,
        per_page: (int | None) = None,
        request_kwargs: (KwargsDict | None) = None,
    ) -> None:
        """Initialize the paginator.

        Version Changed:
            7.1:
            Made arguments keyword-only.

        Args:
            start (int, optional):
                The starting page.

                Whether this is 0-based or 1-based depends on the hosting
                service.

            per_page (int, optional):
                The number of items per page.

            request_kwargs (dict, optional):
                Keyword arguments to pass when making a request.
        """
        self.start = start
        self.per_page = per_page
        self.page_data = None
        self.total_count = None
        self.request_kwargs = request_kwargs or {}

    @property
    def has_prev(self) -> bool:
        """Whether there's a previous page available.

        Subclasses must override this to provide a meaningful value.

        Type:
            bool
        """
        raise NotImplementedError

    @property
    def has_next(self) -> bool:
        """Whether there's a next page available.

        Subclasses must override this to provide a meaningful value.

        Type:
            bool
        """
        raise NotImplementedError

    def prev(self) -> _PageDataT | None:
        """Fetch the previous page, returning the page data.

        Subclasses must override this to provide the logic for fetching pages.

        Returns:
            object:
            The resulting page data.

            This will usually be a :py:class:`list`, but is
            implementation-dependent.

        Raises:
            InvalidPageError:
                There was no previous page to fetch.
        """
        raise NotImplementedError

    def next(self) -> _PageDataT | None:
        """Fetch the next page, returning the page data.

        Subclasses must override this to provide the logic for fetching pages.

        Returns:
            object:
            The resulting page data.

            This will usually be a :py:class:`list`, but is
            implementation-dependent.

        Raises:
            InvalidPageError:
                There was no next page to fetch.
        """
        raise NotImplementedError

    def iter_items(
        self,
        max_pages: (int | None) = None,
    ) -> Iterator[_PageDataItemT]:
        """Iterate through all items across pages.

        This will repeatedly fetch pages, iterating through all items and
        providing them to the caller.

        The maximum number of pages can be capped, to limit the impact on
        the server.

        Args:
            max_pages (int, optional):
                The maximum number of pages to iterate through.

        Yields:
            object:
            Each item from each page's payload.
        """
        for page in self.iter_pages(max_pages=max_pages):
            if page:
                assert isinstance(page, Sequence), (
                    f"page_data is not a sequence (it's a {type(page)}). This "
                    f"is either an unexpected result, or "
                    f"{type(self).__name__}.iter_items() needs to be "
                    "overridden."
                )

                yield from page

    def iter_pages(
        self,
        max_pages: (int | None) = None,
    ) -> Iterator[_PageDataT | None]:
        """Iterate through pages of results.

        This will repeatedly fetch pages, providing each parsed page payload
        to the caller.

        The maximum number of pages can be capped, to limit the impact on
        the server.

        Args:
            max_pages (int, optional):
                The maximum number of pages to iterate through.

        Yields:
            object:
            The parsed payload for each page.
        """
        try:
            if max_pages is None:
                while True:
                    yield self.page_data
                    self.next()
            else:
                for i in range(max_pages):
                    if i > 0:
                        self.next()

                    yield self.page_data
        except InvalidPageError:
            pass

    def __iter__(self) -> Iterator[_PageDataT | None]:
        """Iterate through pages of results.

        This is a simple wrapper for :py:meth:`iter_pages`.

        Yields:
            object:
            The parsed payload for each page.
        """
        yield from self.iter_pages()


class APIPaginator(BasePaginator[_PageDataItemT, _PageDataT]):
    """Handles pagination for API requests to a hosting service.

    Hosting services may provide subclasses of ``APIPaginator`` that can handle
    paginating their specific APIs. These make it easy to fetch pages of data
    from the API, and also works as a bridge for Review Board's web API
    resources.

    All ``APIPaginators`` are expected to take an instance of a
    :py:class:`~reviewboard.hostingsvcs.base.client.HostingServiceClient`
    subclass, and the starting URL (without any arguments for pagination).

    Subclasses can access the
    :py:class:`~reviewboard.hostingsvcs.base.client.HostingServiceClient`
    through the :py:attr:`client` member of the paginator in order to perform
    requests against the hosting service.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.utils.paginator` to
          :py:mod:`reviewboard.hostingsvcs.base.paginator`.

        * This is now a generic, supporting typing for page data and items.
    """

    #: Query parameter name for the start page in a request.
    #:
    #: This is optional. Clients can specify this to provide this as part
    #: of pagination queries.
    #:
    #: Type:
    #:     str
    start_query_param: (str | None) = None

    #: Query parameter name for the requested number of results per page.
    #:
    #: This is optional. Clients can specify this to provide this as part
    #: of pagination queries.
    #:
    #: Type:
    #:     str
    per_page_query_param: (str | None) = None

    ######################
    # Instance variables #
    ######################

    #: The hosting service client used to make requests.
    #:
    #: Type:
    #:     reviewboard.hostingsvcs.base.client.HostingServiceClient
    client: HostingServiceClient

    #: The URL for the next set of results in the page.
    #:
    #: Type:
    #:     str
    next_url: str | None

    #: HTTP headers returned for the current page.
    #:
    #: Type:
    #:     dict
    page_headers: HTTPHeaders | None

    #: The URL for the previous set of results in the page.
    #:
    #: Type:
    #:     str
    prev_url: str | None

    #: The URL used to fetch the current page of data.
    #:
    #: Type:
    #:     str
    url: str | None

    @deprecate_non_keyword_only_args(RemovedInReviewBoard90Warning)
    def __init__(
        self,
        *,
        client: HostingServiceClient | None,
        url: str,
        query_params: QueryArgs = {},
        start: (int | None) = None,
        per_page: (int | None) = None,
        request_kwargs: (KwargsDict | None) = None,
    ) -> None:
        """Initialize the paginator.

        Once initialized, the first page will be fetched automatically.

        Version Changed:
            7.1:
            * Made arguments keyword-only.
            * Explicitly listed out arguments that are passed to the base
              class.

        Args:
            client (reviewboard.hostingsvcs.base.client.HostingServiceClient):
                The hosting service client used to make requests.

            url (str):
                The URL used to make requests.

            query_params (dict):
                The query parameters to append to the URL for requests.

                This will be updated with :py:attr:`start_query_param`
                and :py:attr:`per_page_query_param`, if set.

            *args (tuple):
                Positional arguments for the parent constructor.

            start (int, optional):
                The starting page.

                Whether this is 0-based or 1-based depends on the hosting
                service.

            per_page (int, optional):
                The number of items per page.

            request_kwargs (dict, optional):
                Keyword arguments to pass when making a request.
        """
        super().__init__(
            start=start,
            per_page=per_page,
            request_kwargs=request_kwargs)

        self.client = client
        self.url = url
        self.prev_url = None
        self.next_url = None
        self.page_headers = None

        # Augment the URL with the provided query parameters.
        query_params = query_params.copy()

        if self.start_query_param and self.start:
            query_params[self.start_query_param] = self.start

        if self.per_page_query_param and self.per_page:
            query_params[self.per_page_query_param] = self.per_page

        self.request_kwargs.setdefault('query', {}).update(query_params)

        self._fetch_page()

    @property
    def has_prev(self) -> bool:
        """Whether there's a previous page available.

        Type:
            bool
        """
        return self.prev_url is not None

    @property
    def has_next(self) -> bool:
        """Whether there's a next page available.

        Type:
            bool
        """
        return self.next_url is not None

    def prev(self) -> _PageDataT | None:
        """Fetch the previous page, returning the page data.

        Returns:
            object:
            The resulting page data.

            This will usually be a :py:class:`list`, but is
            implementation-dependent.

        Raises:
            InvalidPageError:
                There was no previous page to fetch.
        """
        if not self.has_prev:
            raise InvalidPageError

        self.url = self.prev_url
        return self._fetch_page()

    def next(self) -> _PageDataT | None:
        """Fetch the next page, returning the page data.

        Returns:
            object:
            The resulting page data.

            This will usually be a :py:class:`list`, but is
            implementation-dependent.

        Raises:
            InvalidPageError:
                There was no next page to fetch.
        """
        if not self.has_next:
            raise InvalidPageError

        self.url = self.next_url
        return self._fetch_page()

    def fetch_url(
        self,
        url: str,
    ) -> APIPaginatorPageData:
        """Fetch the URL, returning information on the page.

        This must be implemented by subclasses.

        Args:
            url (str):
                The URL to fetch.

        Returns:
            dict:
            The pagination information with the above fields.

            See :py:class:`APIPaginatorPageData` for the supported fields.
        """
        raise NotImplementedError

    def _fetch_page(self) -> _PageDataT | None:
        """Fetch a page and extracts the information from it.

        Returns:
            object:
            The resulting page data.

            This will usually be a :py:class:`list`, but is
            implementation-dependent.
        """
        assert self.url is not None
        page_info = self.fetch_url(self.url)

        self.prev_url = page_info.get('prev_url')
        self.next_url = page_info.get('next_url')
        self.per_page = page_info.get('per_page', self.per_page)
        self.page_data = page_info.get('data')
        self.page_headers = page_info.get('headers', {})
        self.total_count = page_info.get('total_count')

        # Make sure the implementation sent the correct data to us.
        assert self.prev_url is None or isinstance(self.prev_url, str), (
            f'"prev_url" result from fetch_url() must be None or Unicode '
            f'string, not {type(self.prev_url)!r}'
        )

        assert self.next_url is None or isinstance(self.next_url, str), (
            f'"next_url" result from fetch_url() must be None or Unicode '
            f'string, not {type(self.next_url)!r}'
        )

        assert self.total_count is None or isinstance(self.total_count, int), (
            f'"total_count" result from fetch_url() must be None or int, not '
            f'{type(self.total_count)!r}'
        )

        assert self.per_page is None or isinstance(self.per_page, int), (
            f'"per_page" result from fetch_url() must be an int, not '
            f'{type(self.per_page)!r}'
        )

        assert isinstance(self.page_headers, dict), (
            f'"page_headers" result from fetch_url() must be a dictionary, '
            f'not {type(self.page_headers)!r}'
        )

        return self.page_data


class ProxyPaginator(BasePaginator[_PageDataItemT, _PageDataT]):
    """A paginator that proxies to another paginator, transforming data.

    This attaches to another paginator, forwarding all requests and proxying
    all data.

    ``ProxyPaginator`` can take the data returned from the other paginator and
    normalize it, transforming it into a new form.

    This is useful when a
    :py:class:`~reviewboard.hostingsvcs.base.hosting_service.
    BaseHostingService` wants to return a paginator to callers that represents
    data in a structured way, using an :py:class:`APIPaginator`'s raw payloads
    as a backing.

    Version Changed:
        6.0:
        * Moved from :py:mod:`reviewboard.hostingsvcs.utils.paginator` to
          :py:mod:`reviewboard.hostingsvcs.base.paginator`.

        * This is now a generic, supporting typing for page data and items.
    """

    ######################
    # Instance variables #
    ######################

    #: The paginator that this is a proxy for.
    #:
    #: Type:
    #:     BasePaginator
    paginator: BasePaginator[Any, Any]

    #: A function used to normalize a page of results from the paginator.
    #:
    #: Type:
    #:     callable
    normalize_page_data_func: (
        _ProxyNormalizePageDataFunc[_PageDataItemT] | None
    )

    def __init__(
        self,
        paginator: BasePaginator[Any, Any],
        normalize_page_data_func: (
            _ProxyNormalizePageDataFunc[_PageDataItemT] | None
        ) = None,
    ) -> None:
        """Initialize the paginator.

        Args:
            paginator (BasePaginator):
                The paginator that this is a proxy for.

            normalize_page_data_func (callable, optional):
                A function used to normalize a page of results from the
                paginator.
        """
        # NOTE: We're not calling BasePaginator here, because we're actually
        #       overriding all the properties it would set that we care about.
        self.paginator = paginator
        self.normalize_page_data_func = normalize_page_data_func
        self.page_data = self.normalize_page_data(self.paginator.page_data)

    @property
    def has_prev(self) -> bool:
        """Whether there's a previous page available.

        Type:
            bool
        """
        return self.paginator.has_prev

    @property
    def has_next(self) -> bool:
        """Whether there's a next page available.

        Type:
            bool
        """
        return self.paginator.has_next

    @property
    def per_page(self) -> int | None:
        """The number of items requested per page.

        Type:
            int
        """
        return self.paginator.per_page

    @property
    def total_count(self) -> int | None:
        """The number of items across all pages, if known.

        Type:
            int
        """
        return self.paginator.total_count

    def prev(self) -> _PageDataT | None:
        """Fetch the previous page, returning the page data.

        Returns:
            object:
            The resulting page data.

            This will usually be a :py:class:`list`, but is
            implementation-dependent.

        Raises:
            InvalidPageError:
                There was no previous page to fetch.
        """
        return self._process_page(self.paginator.prev())

    def next(self) -> _PageDataT | None:
        """Fetch the next page, returning the page data.

        Returns:
            object:
            The resulting page data.

            This will usually be a :py:class:`list`, but is
            implementation-dependent.

        Raises:
            InvalidPageError:
                There was no next page to fetch.
        """
        return self._process_page(self.paginator.next())

    def normalize_page_data(
        self,
        data: Any,
    ) -> _PageDataT | None:
        """Normalize a page of data.

        If :py:attr:`normalize_page_data_func` was passed on construction, this
        will call it, passing in the page data. That will then be returned.

        This can be overridden by subclasses that want to do more complex
        processing without requiring ``normalize_page_data_func`` to be
        passed in.

        Args:
            data (object):
                The data to normalize.

        Returns:
            object:
            The resulting data.
        """
        if callable(self.normalize_page_data_func):
            data = self.normalize_page_data_func(data)

        return data

    def _process_page(
        self,
        page_data: Any,
    ) -> _PageDataT | None:
        """Process a page of data.

        This will normalize the page data, store it, and return it.

        Args:
            page_data (object):
                The data to process.

        Returns:
            object:
            The resulting data.
        """
        self.page_data = self.normalize_page_data(page_data)

        return self.page_data
