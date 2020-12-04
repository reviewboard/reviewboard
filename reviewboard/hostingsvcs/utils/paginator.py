"""Paginators for iterating over API results."""

from __future__ import unicode_literals

from django.utils import six
from django.utils.six.moves import range
from django.utils.six.moves.urllib.parse import (parse_qs, urlencode,
                                                 urlsplit, urlunsplit)


class InvalidPageError(Exception):
    """An error representing an invalid page access."""


class BasePaginator(object):
    """Base class for a paginator used in the hosting services code.

    This provides the basic state and stubbed functions for a simple
    paginator. Subclasses can build upon this to offer more advanced
    functionality.

    Attributes:
        page_data (object):
            The data for the current page. This is implementation-dependent,
            but will usually be a list.

        per_page (int):
            The number of items to fetch per page.

        request_kwargs (dict):
            Keyword arguments to pass when making HTTP requests.

        start (int):
            The starting page. Whether this is 0-based or 1-based depends
            on the hosting service.

        total_count (int):
            The total number of results across all pages. This will be ``None``
            if the value isn't known.
    """

    def __init__(self, start=None, per_page=None, request_kwargs=None):
        """Initialize the paginator.

        Args:
            start (int, optional):
                The starting page. Whether this is 0-based or 1-based depends
                on the hosting service.

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
    def has_prev(self):
        """Whether there's a previous page available.

        Subclasses must override this to provide a meaningful value.
        """
        raise NotImplementedError

    @property
    def has_next(self):
        """Whether there's a next page available.

        Subclasses must override this to provide a meaningful value.
        """
        raise NotImplementedError

    def prev(self):
        """Fetch the previous page, returning the page data.

        Subclasses must override this to provide the logic for fetching pages.

        Returns:
            object:
            The resulting page data. This will usually be a :py:class:`list`,
            but is implementation-dependent.

        Raises:
            InvalidPageError:
                There was no previous page to fetch.
        """
        raise NotImplementedError

    def next(self):
        """Fetch the next page, returning the page data.

        Subclasses must override this to provide the logic for fetching pages.

        Returns:
            object:
            The resulting page data. This will usually be a :py:class:`list`,
            but is implementation-dependent.

        Raises:
            InvalidPageError:
                There was no next page to fetch.
        """
        raise NotImplementedError

    def iter_items(self, max_pages=None):
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
            for data in self.page_data:
                yield data

    def iter_pages(self, max_pages=None):
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

    def __iter__(self):
        """Iterate through pages of results.

        This is a simple wrapper for :py:meth:`iter_pages`.

        Yields:
            object:
            The parsed payload for each page.
        """
        for page in self.iter_pages():
            yield page


class APIPaginator(BasePaginator):
    """Handles pagination for API requests to a hosting service.

    Hosting services may provide subclasses of ``APIPaginator`` that can handle
    paginating their specific APIs. These make it easy to fetch pages of data
    from the API, and also works as a bridge for Review Board's web API
    resources.

    All ``APIPaginators`` are expected to take an instance of a
    :py:class:`~reviewboard.hostingsvcs.service.HostingServiceClient` subclass,
    and the starting URL (without any arguments for pagination).

    Subclasses can access the
    :py:class:`~reviewboard.hostingsvcs.service.HostingServiceClient` through
    the :py:attr:`client` member of the paginator in order to perform requests
    against the hosting service.

    Attributes:
        client (reviewboard.hostingsvcs.service.HostingServiceClient):
            The hosting service client used to make requests.

        next_url (unicode):
            The URL for the next set of results in the page.

        page_headers (dict):
            HTTP headers returned for the current page.

        prev_url (unicode):
            The URL for the previous set of results in the page.

        url (unicode):
            The URL used to fetch the current page of data.
    """

    #: Query parameter name for the start page in a request.
    #:
    #: This is optional. Clients can specify this to provide this as part
    #: of pagination queries.
    start_query_param = None

    #: Query parameter name for the requested number of results per page.
    #:
    #: This is optional. Clients can specify this to provide this as part
    #: of pagination queries.
    per_page_query_param = None

    def __init__(self, client, url, query_params={}, *args, **kwargs):
        """Initialize the paginator.

        Once initialized, the first page will be fetched automatically.

        Args:
            client (reviewboard.hostingsvcs.service.HostingServiceClient):
                The hosting service client used to make requests.

            url (unicode):
                The URL used to make requests.

            query_params (dict):
                The query parameters to append to the URL for requests.
                This will be updated with :py:attr:`start_query_param`
                and :py:attr:`per_page_query_param`, if set.

            *args (tuple):
                Positional arguments for the parent constructor.

            **kwargs (dict):
                Keyword arguments for the parent constructor.
        """
        super(APIPaginator, self).__init__(*args, **kwargs)

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
    def has_prev(self):
        """Whether there's a previous page available."""
        return self.prev_url is not None

    @property
    def has_next(self):
        """Whether there's a next page available."""
        return self.next_url is not None

    def prev(self):
        """Fetch the previous page, returning the page data.

        Returns:
            object:
            The resulting page data. This will usually be a :py:class:`list`,
            but is implementation-dependent.

        Raises:
            InvalidPageError:
                There was no previous page to fetch.
        """
        if not self.has_prev:
            raise InvalidPageError

        self.url = self.prev_url
        return self._fetch_page()

    def next(self):
        """Fetch the next page, returning the page data.

        Returns:
            object:
            The resulting page data. This will usually be a :py:class:`list`,
            but is implementation-dependent.

        Raises:
            InvalidPageError:
                There was no next page to fetch.
        """
        if not self.has_next:
            raise InvalidPageError

        self.url = self.next_url
        return self._fetch_page()

    def fetch_url(self, url):
        """Fetch the URL, returning information on the page.

        This must be implemented by subclasses. It must return a dictionary
        with the following fields:

        ``data`` (:py:class:`object`)
            The data from the page (generally as a list).

        ``headers`` (:py:class:`dict`)
            The headers from the page response.

        ``total_count`` (:py:class:`int`, optional)
            The optional total number of items across all pages.

        ``per_page`` (:py:class:`int`, optional)
            The optional limit on the number of items fetched on each page.

        ``prev_url`` (:py:class:`unicode`, optional)
            The optional URL to the previous page.

        ``next_url`` (:py:class:`unicode`, optional)
            The optional URL to the next page.

        Args:
            url (unicode):
                The URL to fetch.

        Returns:
            dict:
            The pagination information with the above fields.
        """
        raise NotImplementedError

    def _fetch_page(self):
        """Fetch a page and extracts the information from it.

        Returns:
            object:
            The resulting page data. This will usually be a :py:class:`list`,
            but is implementation-dependent.
        """
        page_info = self.fetch_url(self.url)

        self.prev_url = page_info.get('prev_url')
        self.next_url = page_info.get('next_url')
        self.per_page = page_info.get('per_page', self.per_page)
        self.page_data = page_info.get('data')
        self.page_headers = page_info.get('headers', {})
        self.total_count = page_info.get('total_count')

        # Make sure the implementation sent the correct data to us.
        assert self.prev_url is None or isinstance(self.prev_url,
                                                   six.text_type), \
            ('"prev_url" result from fetch_url() must be None or Unicode '
             'string, not %r'
             % type(self.prev_url))

        assert self.next_url is None or isinstance(self.next_url,
                                                   six.text_type), \
            ('"next_url" result from fetch_url() must be None or Unicode '
             'string, not %r'
             % type(self.next_url))

        assert self.total_count is None or isinstance(self.total_count, int), \
            ('"total_count" result from fetch_url() must be None or int, not '
             '%r'
             % type(self.total_count))

        assert self.per_page is None or isinstance(self.per_page, int), \
            ('"per_page" result from fetch_url() must be an int, not %r'
             % type(self.per_page))

        assert isinstance(self.page_headers, dict), \
            ('"page_headers" result from fetch_url() must be a dictionary, '
             'not %r'
             % type(self.page_headers))

        return self.page_data


class ProxyPaginator(BasePaginator):
    """A paginator that proxies to another paginator, transforming data.

    This attaches to another paginator, forwarding all requests and proxying
    all data.

    ``ProxyPaginator`` can take the data returned from the other paginator and
    normalize it, transforming it into a new form.

    This is useful when a
    :py:class:`~reviewboard.hostingsvcs.service.HostingService` wants to return
    a paginator to callers that represents data in a structured way, using an
    :py:class:`APIPaginator`'s raw payloads as a backing.

    Attributes:
        paginator (BasePaginator):
            The paginator that this is a proxy for.

        normalize_page_data_func (callable):
            A function used to normalize a page of results from the paginator.
    """

    def __init__(self, paginator, normalize_page_data_func=None):
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
    def has_prev(self):
        """Whether there's a previous page available."""
        return self.paginator.has_prev

    @property
    def has_next(self):
        """Whether there's a next page available."""
        return self.paginator.has_next

    @property
    def per_page(self):
        """The number of items requested per page."""
        return self.paginator.per_page

    @property
    def total_count(self):
        """The number of items across all pages, if known."""
        return self.paginator.total_count

    def prev(self):
        """Fetch the previous page, returning the page data.

        Returns:
            object:
            The resulting page data. This will usually be a :py:class:`list`,
            but is implementation-dependent.

        Raises:
            InvalidPageError:
                There was no previous page to fetch.
        """
        return self._process_page(self.paginator.prev())

    def next(self):
        """Fetch the next page, returning the page data.

        Returns:
            object:
            The resulting page data. This will usually be a :py:class:`list`,
            but is implementation-dependent.

        Raises:
            InvalidPageError:
                There was no next page to fetch.
        """
        return self._process_page(self.paginator.next())

    def normalize_page_data(self, data):
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

    def _process_page(self, page_data):
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
