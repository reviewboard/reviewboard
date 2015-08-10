from __future__ import unicode_literals

from django.http import HttpResponse
from django.utils import six
from django.utils.encoding import force_unicode
from djblets.util.http import (get_http_requested_mimetype,
                               get_url_params_except,
                               is_mimetype_a)
from djblets.webapi.encoders import (JSONEncoderAdapter, WebAPIEncoder,
                                     XMLEncoderAdapter,
                                     get_registered_encoders)
from djblets.webapi.errors import INVALID_FORM_DATA


class WebAPIResponse(HttpResponse):
    """An API response, formatted for the desired file format."""
    supported_mimetypes = [
        'application/json',
        'application/xml',
    ]

    def __init__(self, request, obj={}, stat='ok', api_format=None,
                 status=200, headers={}, encoders=[],
                 encoder_kwargs={}, mimetype=None, supported_mimetypes=None):
        if not api_format:
            if request.method == 'GET':
                api_format = request.GET.get('api_format', None)
            else:
                api_format = request.POST.get('api_format', None)

        if not supported_mimetypes:
            supported_mimetypes = self.supported_mimetypes

        if not mimetype:
            if not api_format:
                mimetype = get_http_requested_mimetype(request,
                                                       supported_mimetypes)
            elif api_format == "json":
                mimetype = 'application/json'
            elif api_format == "xml":
                mimetype = 'application/xml'

        if not mimetype:
            self.status_code = 400
            self.content_set = True
            return

        if not request.is_ajax() and request.FILES:
            # When uploading a file using AJAX to a webapi view,
            # we must set the mimetype to text/plain. If we use
            # application/json instead, the browser will ask the user
            # to save the file. It's not great, but it's what we must do.
            mimetype = 'text/plain'

        super(WebAPIResponse, self).__init__(content_type=mimetype,
                                             status=status)
        self.request = request
        self.callback = request.GET.get('callback', None)
        self.api_data = {'stat': stat}
        self.api_data.update(obj)
        self.content_set = False
        self.mimetype = mimetype
        self.encoders = encoders or get_registered_encoders()
        self.encoder_kwargs = encoder_kwargs

        for header, value in six.iteritems(headers):
            self[header] = value

        # Prevent IE8 from trying to download some AJAX responses as if they
        # were files.
        self['X-Content-Type-Options'] = 'nosniff'

    def _get_content(self):
        """Returns the API response content in the appropriate format.

        This is an overridden version of HttpResponse._get_content that
        generates the resulting content when requested, rather than
        generating it up-front in the constructor. This is used so that
        the @webapi decorator can set the appropriate API format before
        the content is generated, but after the response is created.
        """
        class MultiEncoder(WebAPIEncoder):
            def __init__(self, encoders):
                self.encoders = encoders

            def encode(self, *args, **kwargs):
                for encoder in self.encoders:
                    result = encoder.encode(*args, **kwargs)

                    if result is not None:
                        return result

                return None

        if not self.content_set:
            adapter = None
            encoder = MultiEncoder(self.encoders)

            # See the note above about the check for text/plain.
            if (self.mimetype == 'text/plain' or
                is_mimetype_a(self.mimetype, 'application/json')):
                adapter = JSONEncoderAdapter(encoder)
            elif is_mimetype_a(self.mimetype, "application/xml"):
                adapter = XMLEncoderAdapter(encoder)
            else:
                assert False

            content = adapter.encode(self.api_data, request=self.request,
                                     **self.encoder_kwargs)

            if self.callback is not None:
                content = "%s(%s);" % (self.callback, content)

            self.content = content
            self.content_set = True

        return super(WebAPIResponse, self).content

    def _set_content(self, value):
        HttpResponse.content.fset(self, value)

    content = property(_get_content, _set_content)


class WebAPIResponsePaginated(WebAPIResponse):
    """A response containing a list of results with pagination.

    This accepts the following parameters to the URL:

    * start - The index of the first item (0-based index).
    * max-results - The maximum number of results to return in the request.

    Subclasses can override much of the pagination behavior of this function.
    While the default behavior operates on a queryset and works on indexes
    within that queryset, subclasses can override this to work on any data
    and paginate in any way they see fit.
    """
    def __init__(self, request, queryset=None, results_key='results',
                 prev_key='prev', next_key='next',
                 total_results_key='total_results',
                 start_param='start', max_results_param='max-results',
                 default_start=0, default_max_results=25, max_results_cap=200,
                 serialize_object_func=None,
                 extra_data={}, *args, **kwargs):
        self.request = request
        self.queryset = queryset
        self.prev_key = prev_key
        self.next_key = next_key
        self.start_param = start_param
        self.max_results_param = max_results_param

        self.start = self.normalize_start(
            request.GET.get(start_param, default_start))

        try:
            self.max_results = \
                min(int(request.GET.get(max_results_param,
                                        default_max_results)),
                    max_results_cap)
        except ValueError:
            self.max_results = default_max_results

        self.results = self.get_results()
        self.total_results = self.get_total_results()

        if self.total_results == 0:
            self.results = []
        elif serialize_object_func:
            self.results = [
                serialize_object_func(obj)
                for obj in self.results
            ]
        else:
            self.results = list(self.results)

        data = {
            results_key: self.results,
            'links': {},
        }
        data.update(extra_data)

        data['links'].update(self.get_links())

        if total_results_key and self.total_results is not None:
            data[total_results_key] = self.total_results

        super(WebAPIResponsePaginated, self).__init__(
            request, obj=data, *args, **kwargs)

    def normalize_start(self, start):
        """Normalizes the start value.

        By default, this ensures it's an integer no less than 0.
        Subclasses can override this behavior.
        """
        try:
            return max(int(start), 0)
        except ValueError:
            return 0

    def has_prev(self):
        """Returns whether there's a previous set of results."""
        return self.start > 0

    def has_next(self):
        """Returns whether there's a next set of results."""
        return self.start + len(self.results) < self.total_results

    def get_prev_index(self):
        """Returns the previous index to use for ?start="""
        return max(0, self.start - self.max_results)

    def get_next_index(self):
        """Returns the next index to use for ?start="""
        return self.start + self.max_results

    def get_results(self):
        """Returns the results for this page."""
        return self.queryset[self.start:self.start + self.max_results]

    def get_total_results(self):
        """Returns the total number of results across all pages.

        Subclasses can return None to prevent this field from showing up
        in the payload.
        """
        return self.queryset.count()

    def get_links(self):
        """Returns all links used in the payload.

        By default, this only includes pagination links. Subclasses can
        provide additional links.
        """
        links = {}

        full_path = self.request.build_absolute_uri(self.request.path)

        query_parameters = get_url_params_except(
            self.request.GET, self.start_param, self.max_results_param)

        if query_parameters:
            query_parameters = '&' + query_parameters

        if self.has_prev():
            links[self.prev_key] = {
                'method': 'GET',
                'href': self.build_pagination_url(
                    full_path, self.get_prev_index(),
                    self.max_results, query_parameters),
            }

        if self.has_next():
            links[self.next_key] = {
                'method': 'GET',
                'href': self.build_pagination_url(
                    full_path, self.get_next_index(),
                    self.max_results, query_parameters),
            }

        return links

    def build_pagination_url(self, full_path, start, max_results,
                             query_parameters):
        """Builds a URL to go to the previous or next set of results."""
        return ('%s?%s=%s&%s=%s%s'
                % (full_path, self.start_param, start,
                   self.max_results_param, max_results,
                   query_parameters))


class WebAPIResponseError(WebAPIResponse):
    """A general API error response.

    This contains an error code and a human-readable message. Additional
    data can be provided through ``extra_params`` and ``headers``.
    """
    def __init__(self, request, err, extra_params={}, headers={},
                 *args, **kwargs):
        errdata = {
            'err': {
                'code': err.code,
                'msg': err.msg
            }
        }
        errdata.update(extra_params)

        headers = headers.copy()

        if callable(err.headers):
            headers.update(err.headers(request))
        else:
            headers.update(err.headers)

        super(WebAPIResponseError, self).__init__(
            request, obj=errdata, stat="fail",
            status=err.http_status, headers=headers,
            *args, **kwargs)


class WebAPIResponseFormError(WebAPIResponseError):
    """An error response designed to return all errors from a form."""
    def __init__(self, request, form, *args, **kwargs):
        fields = {}

        for field in form.errors:
            fields[field] = [force_unicode(e) for e in form.errors[field]]

        super(WebAPIResponseFormError, self).__init__(
            request, INVALID_FORM_DATA,
            {
                'fields': fields
            },
            *args, **kwargs)
