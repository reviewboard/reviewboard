from __future__ import unicode_literals

from django.utils import six
from django.utils.six.moves.urllib.parse import (parse_qs, urlencode,
                                                 urlsplit, urlunsplit)


class InvalidPageError(Exception):
    """An error representing an invalid page access."""
    pass


class BasePaginator(object):
    """Base class for a paginator used in the hosting services code.

    This provides the basic state and stubbed functions for a simple
    paginator. Subclasses can build upon this to offer more advanced
    functionality.
    """
    def __init__(self, start=None, per_page=None):
        self.start = start
        self.per_page = per_page
        self.page_data = None
        self.total_count = None

    @property
    def has_prev(self):
        """Returns whether there's a previous page available.

        Subclasses must override this to provide a meaningful
        return value.
        """
        raise NotImplementedError

    @property
    def has_next(self):
        """Returns whether there's a next page available.

        Subclasses must override this to provide a meaningful
        return value.
        """
        raise NotImplementedError

    def prev(self):
        """Fetches the previous page, returning the page data.

        Subclasses must override this to provide the logic for
        fetching pages.

        If there isn't a previous page available, this must raise
        InvalidPageError.
        """
        raise NotImplementedError

    def next(self):
        """Fetches the previous page, returning the page data.

        Subclasses must override this to provide the logic for
        fetching pages.

        If there isn't a next page available, this must raise
        InvalidPageError.
        """
        raise NotImplementedError


class APIPaginator(BasePaginator):
    """Handles pagination for API requests to a hosting service.

    Hosting services may provide subclasses of APIPaginator that can
    handle paginating their specific APIs. These make it easy to fetch
    pages of data from the API, and also works as a bridge for
    Review Board's web API resources.

    All APIPaginators are expected to take an instance of a
    HostingServiceClient subclass, and the starting URL (without any
    arguments for pagination).

    Subclasses can access the HostingServiceClient through the ``client``
    member of the paginator in order to perform requests against the
    HostingService.
    """
    #: The optional query parameter name used to specify the start page in
    #: a request.
    start_query_param = None

    #: The optional query parameter name used to specify the requested number
    #: of results per page.
    per_page_query_param = None

    def __init__(self, client, url, query_params={}, *args, **kwargs):
        super(APIPaginator, self).__init__(*args, **kwargs)

        self.client = client
        self.prev_url = None
        self.next_url = None
        self.page_headers = None

        # Augment the URL with the provided query parameters.
        query_params = query_params.copy()

        if self.start_query_param and self.start:
            query_params[self.start_query_param] = self.start

        if self.per_page_query_param and self.per_page:
            query_params[self.per_page_query_param] = self.per_page

        self.url = self._add_query_params(url, query_params)

        self._fetch_page()

    @property
    def has_prev(self):
        """Returns whether there's a previous page available."""
        return self.prev_url is not None

    @property
    def has_next(self):
        """Returns whether there's a next page available."""
        return self.next_url is not None

    def prev(self):
        """Fetches the previous page, returning the page data.

        If there isn't a next page available, this will raise
        InvalidPageError.
        """
        if not self.has_prev:
            raise InvalidPageError

        self.url = self.prev_url
        return self._fetch_page()

    def next(self):
        """Fetches the next page, returning the page data.

        If there isn't a next page available, this will raise
        InvalidPageError.
        """
        if not self.has_next:
            raise InvalidPageError

        self.url = self.next_url
        return self._fetch_page()

    def fetch_url(self, url):
        """Fetches the URL, returning information on the page.

        This must be implemented by subclasses. It must return a dictionary
        with the following fields:

        * data        - The data from the page (generally as a list).
        * headers     - The headers from the page response.
        * total_count - The optional total number of items across all pages.
        * per_page    - The optional limit on the number of items fetched
                        on each page.
        * prev_url    - The optional URL to the previous page.
        * next_url    - The optional URL to the next page.
        """
        raise NotImplementedError

    def _fetch_page(self):
        """Fetches a page and extracts the information from it."""
        page_info = self.fetch_url(self.url)

        self.prev_url = page_info.get('prev_url')
        self.next_url = page_info.get('next_url')
        self.per_page = page_info.get('per_page', self.per_page)
        self.page_data = page_info.get('data')
        self.page_headers = page_info.get('headers')
        self.total_count = page_info.get('total_count')

        return self.page_data

    def _add_query_params(self, url, new_query_params):
        """Adds query parameters onto the given URL."""
        scheme, netloc, path, query_string, fragment = urlsplit(url)
        query_params = parse_qs(query_string)
        query_params.update(new_query_params)
        new_query_string = urlencode(
            [
                (key, value)
                for key, value in sorted(six.iteritems(query_params),
                                         key=lambda i: i[0])
            ],
            doseq=True)

        return urlunsplit((scheme, netloc, path, new_query_string, fragment))


class ProxyPaginator(BasePaginator):
    """A paginator that proxies to another paginator, transforming data.

    This attaches to another paginator, forwarding all requests and proxying
    all data.

    The ProxyPaginator can take the data returned from the other paginator
    and normalize it, transforming it into a new form.

    This is useful when a HostingService wants to return a paginator to
    callers that represents data in a structured way, using an APIPaginator's
    raw payloads as a backing.
    """
    def __init__(self, paginator, normalize_page_data_func=None):
        # NOTE: We're not calling BasePaginator here, because we're actually
        #       overriding all the properties it would set that we care about.
        self.paginator = paginator
        self.normalize_page_data_func = normalize_page_data_func
        self.page_data = self.normalize_page_data(self.paginator.page_data)

    @property
    def has_prev(self):
        """Returns whether there's a previous page available."""
        return self.paginator.has_prev

    @property
    def has_next(self):
        """Returns whether there's a next page available."""
        return self.paginator.has_next

    @property
    def per_page(self):
        """Returns the number of items requested per page."""
        return self.paginator.per_page

    @property
    def total_count(self):
        """Returns the number of items across all pages, if known."""
        return self.paginator.total_count

    def prev(self):
        """Fetches the previous page, returning the page data.

        If there isn't a next page available, this will raise
        InvalidPageError.
        """
        return self._process_page(self.paginator.prev())

    def next(self):
        """Fetches the next page, returning the page data.

        If there isn't a next page available, this will raise
        InvalidPageError.
        """
        return self._process_page(self.paginator.next())

    def normalize_page_data(self, data):
        """Normalizes a page of data.

        If ``normalize_page_data_func`` was passed on construction, this
        will call it, passing in the page data. That will then be returned.

        This can be overridden by subclasses that want to do more complex
        processing without requiring ``normalize_page_data_func`` to be
        passed in.
        """
        if callable(self.normalize_page_data_func):
            data = self.normalize_page_data_func(data)

        return data

    def _process_page(self, page_data):
        """Processes a page of data.

        This will normalize the page data, store it, and return it.
        """
        self.page_data = self.normalize_page_data(page_data)

        return self.page_data
