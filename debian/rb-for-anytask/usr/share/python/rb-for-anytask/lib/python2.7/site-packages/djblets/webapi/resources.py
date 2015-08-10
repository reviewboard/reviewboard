from __future__ import unicode_literals

import warnings

from django.conf.urls import include, patterns, url
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.fields.related import (
    ManyRelatedObjectsDescriptor,
    ReverseManyRelatedObjectsDescriptor,
    ReverseSingleRelatedObjectDescriptor)
from django.db.models.query import QuerySet
from django.http import (HttpResponseNotAllowed, HttpResponse,
                         HttpResponseNotModified)
from django.utils import six
from django.views.decorators.vary import vary_on_headers

from djblets.util.decorators import augment_method_from
from djblets.util.http import (get_modified_since, encode_etag,
                               etag_if_none_match,
                               set_last_modified, set_etag,
                               get_http_requested_mimetype)
from djblets.urls.patterns import never_cache_patterns
from djblets.webapi.auth import check_login
from djblets.webapi.responses import (WebAPIResponse,
                                      WebAPIResponseError,
                                      WebAPIResponsePaginated)
from djblets.webapi.decorators import (SPECIAL_PARAMS,
                                       webapi_login_required,
                                       webapi_request_fields,
                                       webapi_response_errors)
from djblets.webapi.errors import (DOES_NOT_EXIST,
                                   LOGIN_FAILED,
                                   NOT_LOGGED_IN,
                                   PERMISSION_DENIED,
                                   WebAPIError)


_model_to_resources = {}
_name_to_resources = {}
_class_to_resources = {}


class WebAPIResource(object):
    """A resource living at a specific URL, representing an object or list
    of objects.

    A WebAPIResource is a RESTful resource living at a specific URL. It
    can represent either an object or a list of objects, and can respond
    to various HTTP methods (GET, POST, PUT, DELETE).

    Subclasses are expected to override functions and variables in order to
    provide specific functionality, such as modifying the resource or
    creating a new resource.


    Representing Models
    -------------------

    Most resources will have ``model`` set to a Model subclass, and
    ``fields`` set to a dictionary defining the fields to return in the
    resource payloads.

    Each resource will also include a ``link`` dictionary that maps
    a key (resource name or action) to a dictionary containing the URL
    (``href``) and the HTTP method that's to be used for that URL
    (``method``). This will include a special ``self`` key that links to
    that resource's actual location.

    An example of this might be::

       'links': {
           'self': {
               'method': 'GET',
               'href': '/path/to/this/resource/'
           },
           'update': {
               'method': 'PUT',
               'href': '/path/to/this/resource/'
           }
       }

    Resources associated with a model may want to override the ``get_queryset``
    function to return a queryset with a more specific query.

    By default, an individual object's key name in the resulting payloads
    will be set to the lowercase class name of the object, and the plural
    version used for lists will be the same but with 's' appended to it. This
    can be overridden by setting ``name`` and ``name_plural``.


    Non-Database Models
    -------------------

    Resources are not always backed by a database model. It's often useful to
    work with lists of objects or data computed within the request.

    In these cases, most resources will still want to set ``model`` to some
    sort of class and provide a ``fields`` dictionary. It's expected that
    the fields will all exist as attributes on an instance of the model, or
    that a serializer function will exist for the field.

    These resources will then to define a ``get_queryset`` that returns a
    :py:class:`djblets.db.query.LocalDataQuerySet` containing the list of
    items to return in the resource. This will allow standard resource
    functionality like pagination to work.


    Matching Objects
    ----------------

    Objects are generally queried by their numeric object ID and mapping that
    to the object's ``pk`` attribute. For this to work, the ``uri_object_key``
    attribute must be set to the name in the regex for the URL that will
    be captured and passed to the handlers for this resource. The
    ``uri_object_key_regex`` attribute can be overridden to specify the
    regex for matching this ID (useful for capturing names instead of
    numeric IDs) and ``model_object_key`` can be overridden to specify the
    model field that will be matched against.


    Parents and URLs
    ----------------

    Resources typically have a parent resource, of which the resource is
    a subclass. Resources will often list their children (by setting
    ``list_child_resources`` and ``item_child_resources`` in a subclass
    to lists of other WebAPIResource instances). This makes the entire tree
    navigatable. The URLs are built up automatically, so long as the result
    of get_url_patterns() from top-level resources are added to the Django
    url_patterns variables commonly found in urls.py.

    Child objects should set the ``model_parent_key`` variable to the
    field name of the object's parent in the resource hierarchy. This
    allows WebAPIResource to build a URL with the right values filled in in
    order to make a URL to this object.

    If the parent is dynamic based on certain conditions, then the
    ``get_parent_object`` function can be overridden instead.


    Object Serialization
    --------------------

    Objects are serialized through the ``serialize_object`` function.
    This rarely needs to be overridden, but can be called from WebAPIEncoders
    in order to serialize the object. By default, this will loop through
    the ``fields`` variable and add each value to the resulting dictionary.

    Values can be specially serialized by creating functions in the form of
    ``serialize_<fieldname>_field``. These functions take the object being
    serialized and must return a value that can be fed to the encoder.

    By default, resources will not necessarily serialize the objects in their
    own payloads. Instead, they will look up the registered resource instance
    for the model using ``get_resource_for_object``, and serialize with that.
    A resource can override that logic for its own payloads by providing
    a custom ``get_serializer_for_object`` method.


    Handling Requests
    -----------------

    WebAPIResource calls the following functions based on the type of
    HTTP request:

      * ``get`` - HTTP GET for individual objects.
      * ``get_list`` - HTTP GET for resources representing lists of objects.
      * ``create`` - HTTP POST on resources representing lists of objects.
                     This is expected to return the object and an HTTP
                     status of 201 CREATED, on success.
      * ``update`` - HTTP PUT on individual objects to modify their state
                     based on full or partial data.
      * ``delete`` - HTTP DELETE on an individual object. This is expected
                     to return a status of HTTP 204 No Content on success.
                     The default implementation just deletes the object.

    Any function that is not implemented will return an HTTP 405 Method
    Not Allowed. Functions that have handlers provided should set
    ``allowed_methods`` to a tuple of the HTTP methods allowed. For example::

        allowed_methods = ('GET', POST', 'DELETE')

    These functions are passed an HTTPRequest and a list of arguments
    captured in the URL and are expected to return standard HTTP response
    codes, along with a payload in most cases. The functions can return any of:

      * A HttpResponse
      * A WebAPIResponse
      * A WebAPIError
      * A tuple of (WebAPIError, Payload)
      * A tuple of (WebAPIError, Payload Dictionary, Headers Dictionary)
      * A tuple of (HTTP status, Payload)
      * A tuple of (HTTP status, Payload Dictionary, Headers Dictionary)

    In general, it's best to return one of the tuples containing an HTTP
    status, and not any object, but there are cases where an object is
    necessary.

    Commonly, a handler will need to fetch parent objects in order to make
    some request. The values for all captured object IDs in the URL are passed
    to the handler, but it's best to not use these directly. Instead, the
    handler should accept a **kwargs parameter, and then call the parent
    resource's ``get_object`` function and pass in that **kwargs. For example::

      def create(self, request, *args, **kwargs):
          try:
              my_parent = myParentResource.get_object(request, *args, **kwargs)
          except ObjectDoesNotExist:
              return DOES_NOT_EXIST


    Pagination
    ----------

    List resources automatically handle pagination of data, when using
    models and querysets. Each request will return a fixed number of
    results, and clients can fetch the previous or next batches through
    the generated ``prev`` and ``next`` links.

    By default, pagination is handled by WebAPIResponsePaginated. This
    is responsible for fetching data from the resource's queryset. It's also
    responsible for interpreting the ``start`` and ``max-results`` query
    parameters, which are assumed to be 0-based indexes into the queryset.

    Resources can override how pagination works by setting ``paginated_cls``
    to a subclass of WebAPIResponsePaginated. Through that, they can customize
    all aspects of pagination for the resource.


    Expanding Resources
    -------------------

    The resulting data returned from a resource will by default provide
    links to child resources. If a lot of aggregated data is needed, then
    instead of making several queries the caller can use the ``?expand=``
    parameter. This takes a comma-separated list of keys in the resource
    names found in the payloads and expands them instead of linking to them.

    This can result in really large downloads, if deep expansion is made
    when accessing lists of resources. However, it can also result in less
    strain on the server if used correctly.


    Faking HTTP Methods
    -------------------

    There are clients that can't actually request anything but HTTP POST
    and HTTP GET. An HTML form is one such example, and Flash applications
    are another. For these cases, an HTTP POST can be made, with a special
    ``_method`` parameter passed to the URL. This can be set to the HTTP
    method that's desired. For example, ``PUT`` or ``DELETE``.


    Permissions
    -----------

    Unless overridden, an object cannot be modified, created, or deleted
    if the user is not logged in and if an appropriate permission function
    does not return True. These permission functions are:

    * ``has_access_permissions`` - Used for HTTP GET calls. Returns True
                                   by default.
    * ``has_modify_permissions`` - Used for HTTP POST or PUT calls, if
                                   called by the subclass. Returns False
                                   by default.
    * ``has_delete_permissions`` - Used for HTTP DELETE permissions. Returns
                                   False by default.


    Browser Caching
    ---------------

    To improve performance, resources can make use of browser-side caching.
    If a resource is accessed more than once, and it hasn't changed,
    the resource will return an :http:`304`.

    There are two methods for caching: Last Modified headers, and ETags.

    Last Modified
    ~~~~~~~~~~~~~

    A resource can set ``last_modified_field`` to the name of a DateTimeField
    in the model. This will be used to determine if the resource has changed
    since the last request.

    If a bit more work is needed, the ``get_last_modified`` function
    can instead be overridden. This takes the request and object and is
    expected to return a timestamp.

    ETags
    ~~~~~

    ETags are arbitrary, unique strings that represent the state of a resource.
    There should only ever be one possible ETag per state of the resource.

    A resource can set the ``etag_field`` to the name of a field in the
    model.

    If no field really works, ``autogenerate_etags`` can be set. This will
    generate a suitable ETag based on all fields in the resource. For this
    to work correctly, no custom data can be added to the payload, and
    links cannot be dynamic.

    If more work is needed, the ``get_etag`` function can instead be
    overridden. It will take a request and object and is expected to return
    a string.


    Mimetypes
    ---------

    Resources should list the possible mimetypes they'll accept and return in
    :py:attr:`allowed_mimetypes`. Each entry in the list is a dictionary
    with 'list' containing a mimetype for resource lists, and 'item'
    containing the equivalent mimetype for a resource item. In the case of
    a singleton, 'item' will contain the mimetype. If the mimetype is not
    applicable to one of the resource forms, the corresponding entry
    should contain None.

    Entries in these lists are checked against the mimetypes requested in the
    HTTP Accept header, and, by default, the returned data will be sent in
    that mimetype. If the requested data is a resource list, the corresponding
    resource item mimetype will also be sent in the 'Item-Content-Type'
    header.

    By default, this lists will have entries with both 'list' and 'item'
    containing :mimetype:`application/json` and :mimetype:`application/xml`,
    along with any resource-specific mimetypes, if used.

    Resource-specific Mimetypes
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    In order to better identify resources, resources can provide their
    own custom mimetypes. These are known as vendor-specific mimetypes, and
    are subsets of :mimetype:`application/json` and
    :mimetype:`application/xml`. An example would be
    :mimetype:`application/vnd.example.com.myresource+json`.

    To enable this on a resource, set :py:attr:`mimetype_vendor` to the
    vendor name. This is often a domain name. For example::

        mimetype_vendor = 'djblets.org'

    The resource names will then be generated based on the name of the
    resource (:py:attr:`name_plural` for resource lists, :py:attr:`name` for
    resource items and singletons). These can be customized as well::

        mimetype_list_resource_name = 'myresource-list'
        mimetype_item_resource_name = 'myresource'

    When these are used, any client requesting either the resource-specific
    mimetype or the more generic mimetype will by default receive a payload
    with the resource-specific mimetype. This makes it easier to identify
    the schema of resource data without hard-coding any knowledge of the
    URI.
    """

    # Configuration
    model = None
    fields = {}
    uri_object_key_regex = r'[0-9]+'
    uri_object_key = None
    model_object_key = 'pk'
    model_parent_key = None
    last_modified_field = None
    etag_field = None
    autogenerate_etags = False
    singleton = False
    list_child_resources = []
    item_child_resources = []
    allowed_methods = ('GET',)
    mimetype_vendor = None
    mimetype_list_resource_name = None
    mimetype_item_resource_name = None
    allowed_mimetypes = [
        {'list': mime, 'item': mime}
        for mime in WebAPIResponse.supported_mimetypes
    ]

    #: The class to use for paginated results in get_list.
    paginated_cls = WebAPIResponsePaginated

    # State
    method_mapping = {
        'GET': 'get',
        'POST': 'post',
        'PUT': 'put',
        'DELETE': 'delete',
    }

    _parent_resource = None
    _mimetypes_cache = None

    def __init__(self):
        _name_to_resources[self.name] = self
        _name_to_resources[self.name_plural] = self
        _class_to_resources[self.__class__] = self

        # Mark this class, and any subclasses, to be Web API handlers
        self.is_webapi_handler = True

        # Copy this list, because otherwise we may modify the class-level
        # version of it.
        self.allowed_mimetypes = list(self.allowed_mimetypes)

        if self.mimetype_vendor:
            # Generate list and item resource-specific mimetypes
            # for each supported mimetype, and add them as a pair to the
            # allowed mimetypes.
            for mimetype_pair in self.allowed_mimetypes:
                vend_mimetype_pair = {
                    'list': None,
                    'item': None,
                }

                for key, is_list in [('list', True), ('item', False)]:
                    if (key in mimetype_pair and
                        (mimetype_pair[key] in
                         WebAPIResponse.supported_mimetypes)):
                        vend_mimetype_pair[key] = \
                            self._build_resource_mimetype(mimetype_pair[key],
                                                          is_list)

                if vend_mimetype_pair['list'] or vend_mimetype_pair['item']:
                    self.allowed_mimetypes.append(vend_mimetype_pair)

    @vary_on_headers('Accept', 'Cookie')
    def __call__(self, request, api_format=None, *args, **kwargs):
        """Invokes the correct HTTP handler based on the type of request."""
        if not hasattr(request, '_djblets_webapi_object_cache'):
            request._djblets_webapi_object_cache = {}

        auth_result = check_login(request)

        if isinstance(auth_result, tuple):
            auth_success, auth_message, auth_headers = auth_result

            if not auth_success:
                err = LOGIN_FAILED

                if auth_message:
                    err = err.with_message(auth_message)

                return WebAPIResponseError(
                    request,
                    err=err,
                    headers=auth_headers or {},
                    api_format=api_format,
                    mimetype=self._build_error_mimetype(request))

        method = request.method

        if method == 'POST':
            # Not all clients can do anything other than GET or POST.
            # So, in the case of POST, we allow overriding the method
            # used.
            method = request.POST.get('_method', kwargs.get('_method', method))
        elif method == 'PUT':
            # Normalize the PUT data so we can get to it.
            # This is due to Django's treatment of PUT vs. POST. They claim
            # that PUT, unlike POST, is not necessarily represented as form
            # data, so they do not parse it. However, that gives us no clean
            # way of accessing the data. So we pretend it's POST for a second
            # in order to parse.
            #
            # This must be done only for legitimate PUT requests, not faked
            # ones using ?method=PUT.
            try:
                request.method = 'POST'
                request._load_post_and_files()
                request.method = 'PUT'
            except AttributeError:
                request.META['REQUEST_METHOD'] = 'POST'
                request._load_post_and_files()
                request.META['REQUEST_METHOD'] = 'PUT'

        request._djblets_webapi_method = method
        request._djblets_webapi_kwargs = kwargs
        request.PUT = request.POST

        if method in self.allowed_methods:
            if (method == "GET" and
                not self.singleton and
                (self.uri_object_key is None or
                 self.uri_object_key not in kwargs)):
                view = self.get_list
            else:
                view = getattr(self, self.method_mapping.get(method, None))
        else:
            view = None

        if view and six.callable(view):
            result = self.call_method_view(
                request, method, view, api_format=api_format, *args, **kwargs)

            if isinstance(result, WebAPIResponse):
                return result
            elif isinstance(result, WebAPIError):
                return WebAPIResponseError(
                    request,
                    err=result,
                    api_format=api_format,
                    mimetype=self._build_error_mimetype(request))
            elif isinstance(result, tuple):
                headers = {}

                if method == 'GET':
                    request_params = request.GET
                else:
                    request_params = request.POST

                if len(result) == 3:
                    headers = result[2]

                if 'Location' in headers:
                    extra_querystr = '&'.join([
                        '%s=%s' % (param, request_params[param])
                        for param in SPECIAL_PARAMS
                        if param in request_params
                    ])

                    if extra_querystr:
                        if '?' in headers['Location']:
                            headers['Location'] += '&' + extra_querystr
                        else:
                            headers['Location'] += '?' + extra_querystr

                if isinstance(result[0], WebAPIError):
                    return WebAPIResponseError(
                        request,
                        err=result[0],
                        headers=headers,
                        extra_params=result[1],
                        api_format=api_format,
                        mimetype=self._build_error_mimetype(request))
                else:
                    response_args = self.build_response_args(request)
                    headers.update(response_args.pop('headers', {}))
                    return WebAPIResponse(
                        request,
                        status=result[0],
                        obj=result[1],
                        headers=headers,
                        api_format=api_format,
                        encoder_kwargs=dict({
                            'calling_resource': self,
                        }, **kwargs),
                        **response_args)
            elif isinstance(result, HttpResponse):
                return result
            else:
                raise AssertionError(result)
        else:
            return HttpResponseNotAllowed(self.allowed_methods)

    def call_method_view(self, request, method, view, *args, **kwargs):
        """Calls the given method view.

        This will just call the given view by default, passing in all
        args and kwargs.

        This can be overridden by subclasses to perform additional
        checks or pass additional data to the view.
        """
        return view(request, *args, **kwargs)

    @property
    def __name__(self):
        return self.__class__.__name__

    @property
    def name(self):
        """Returns the name of the object, used for keys in the payloads."""
        if not hasattr(self, '_name'):
            if self.model:
                self._name = self.model.__name__.lower()
            else:
                self._name = self.__name__.lower()

        return self._name

    @property
    def name_plural(self):
        """Returns the plural name of the object, used for lists."""
        if not hasattr(self, '_name_plural'):
            if self.singleton:
                self._name_plural = self.name
            else:
                self._name_plural = self.name + 's'

        return self._name_plural

    @property
    def item_result_key(self):
        """Returns the key for single objects in the payload."""
        return self.name

    @property
    def list_result_key(self):
        """Returns the key for lists of objects in the payload."""
        return self.name_plural

    @property
    def uri_name(self):
        """Returns the name of the resource in the URI.

        This can be overridden when the name in the URI needs to differ
        from the name used for the resource.
        """
        return self.name_plural.replace('_', '-')

    @property
    def link_name(self):
        """Returns the name of the resource for use in a link.

        This can be overridden when the name in the link needs to differ
        from the name used for the resource.
        """
        return self.name_plural

    def _build_resource_mimetype(self, mimetype, is_list):
        if is_list:
            resource_name = (self.mimetype_list_resource_name or
                             self.name_plural.replace('_', '-'))
        else:
            resource_name = (self.mimetype_item_resource_name or
                             self.name.replace('_', '-'))

        return self._build_vendor_mimetype(mimetype, resource_name)

    def _build_error_mimetype(self, request):
        mimetype = get_http_requested_mimetype(
            request, WebAPIResponse.supported_mimetypes)

        if self.mimetype_vendor:
            mimetype = self._build_vendor_mimetype(mimetype, 'error')

        return mimetype

    def _build_vendor_mimetype(self, mimetype, name):
        parts = mimetype.split('/')

        return '%s/vnd.%s.%s+%s' % (parts[0],
                                    self.mimetype_vendor,
                                    name,
                                    parts[1])

    def build_response_args(self, request):
        is_list = (request._djblets_webapi_method == 'GET' and
                   not self.singleton and
                   (self.uri_object_key is None or
                    self.uri_object_key not in request._djblets_webapi_kwargs))

        if is_list:
            key = 'list'
        else:
            key = 'item'

        supported_mimetypes = [
            mime[key]
            for mime in self.allowed_mimetypes
            if mime.get(key)
        ]

        mimetype = get_http_requested_mimetype(request, supported_mimetypes)

        if (self.mimetype_vendor and
            mimetype in WebAPIResponse.supported_mimetypes):
            mimetype = self._build_resource_mimetype(mimetype, is_list)

        response_args = {
            'supported_mimetypes': supported_mimetypes,
            'mimetype': mimetype,
        }

        if is_list:
            for mimetype_pair in self.allowed_mimetypes:
                if (mimetype_pair.get('list') == mimetype and
                    mimetype_pair.get('item')):
                    response_args['headers'] = {
                        'Item-Content-Type': mimetype_pair['item'],
                    }
                    break

        return response_args

    def get_object(self, request, id_field=None, *args, **kwargs):
        """Returns an object, given captured parameters from a URL.

        This will perform a query for the object, taking into account
        ``model_object_key``, ``uri_object_key``, and any captured parameters
        from the URL.

        This requires that ``model`` and ``uri_object_key`` be set.

        Throws django.core.exceptions.ObjectDoesNotExist if the requested
        object does not exist.
        """
        assert self.model
        assert self.singleton or self.uri_object_key

        if self.singleton:
            cache_key = '%d' % id(self)
        else:
            id_field = id_field or self.model_object_key
            object_id = kwargs[self.uri_object_key]
            cache_key = '%d:%s:%s' % (id(self), id_field, object_id)

        if cache_key in request._djblets_webapi_object_cache:
            return request._djblets_webapi_object_cache[cache_key]

        if 'is_list' in kwargs:
            # Don't pass this in to _get_queryset, since we're not fetching
            # a list, and don't want the extra optimizations for lists to
            # kick in.
            del kwargs['is_list']

        queryset = self._get_queryset(request, *args, **kwargs)

        if self.singleton:
            obj = queryset.get()
        else:
            obj = queryset.get(**{
                id_field: object_id,
            })

        request._djblets_webapi_object_cache[cache_key] = obj

        return obj

    def post(self, *args, **kwargs):
        """Handles HTTP POSTs.

        This is not meant to be overridden unless there are specific needs.

        This will invoke ``create`` if doing an HTTP POST on a list resource.

        By default, an HTTP POST is not allowed on individual object
        resourcces.
        """

        if 'POST' not in self.allowed_methods:
            return HttpResponseNotAllowed(self.allowed_methods)

        if (self.uri_object_key is None or
            kwargs.get(self.uri_object_key, None) is None):
            return self.create(*args, **kwargs)

        # Don't allow POSTs on children by default.
        allowed_methods = list(self.allowed_methods)
        allowed_methods.remove('POST')

        return HttpResponseNotAllowed(allowed_methods)

    def put(self, request, *args, **kwargs):
        """Handles HTTP PUTs.

        This is not meant to be overridden unless there are specific needs.

        This will just invoke ``update``.
        """
        return self.update(request, *args, **kwargs)

    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def get(self, request, api_format, *args, **kwargs):
        """Handles HTTP GETs to individual object resources.

        By default, this will check for access permissions and query for
        the object. It will then return a serialized form of the object.

        This may need to be overridden if needing more complex logic.
        """
        if (not self.model or
            (self.uri_object_key is None and not self.singleton)):
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            obj = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_access_permissions(request, obj, *args, **kwargs):
            return self.get_no_access_error(request, obj=obj, *args, **kwargs)

        last_modified_timestamp = self.get_last_modified(request, obj)
        etag = self.get_etag(request, obj, **kwargs)

        if self.are_cache_headers_current(request, last_modified_timestamp,
                                          etag):
            return HttpResponseNotModified()

        data = {
            self.item_result_key: self.serialize_object(obj, request=request,
                                                        *args, **kwargs),
        }

        response = WebAPIResponse(request,
                                  status=200,
                                  obj=data,
                                  api_format=api_format,
                                  **self.build_response_args(request))

        if last_modified_timestamp:
            set_last_modified(response, last_modified_timestamp)

        if etag:
            set_etag(response, etag)

        return response

    @webapi_response_errors(NOT_LOGGED_IN, PERMISSION_DENIED, DOES_NOT_EXIST)
    @webapi_request_fields(
        optional={
            'start': {
                'type': int,
                'description': 'The 0-based index of the first result in '
                               'the list. The start index is usually the '
                               'previous start index plus the number of '
                               'previous results. By default, this is 0.',
            },
            'max-results': {
                'type': int,
                'description': 'The maximum number of results to return in '
                               'this list. By default, this is 25. There is '
                               'a hard limit of 200; if you need more than '
                               '200 results, you will need to make more '
                               'than one request, using the "next" '
                               'pagination link.',
            }
        },
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Handles HTTP GETs to list resources.

        By default, this will query for a list of objects and return the
        list in a serialized form.
        """
        data = {
            'links': self.get_links(self.list_child_resources,
                                    request=request, *args, **kwargs),
        }

        if not self.has_list_access_permissions(request, *args, **kwargs):
            return self.get_no_access_error(request, *args, **kwargs)

        if self.model:
            try:
                queryset = self._get_queryset(request, is_list=True,
                                              *args, **kwargs)
            except ObjectDoesNotExist:
                return DOES_NOT_EXIST

            return self.paginated_cls(
                request,
                queryset=queryset,
                results_key=self.list_result_key,
                serialize_object_func=lambda obj:
                    self.get_serializer_for_object(obj).serialize_object(
                        obj, request=request, *args, **kwargs),
                extra_data=data,
                **self.build_response_args(request))
        else:
            return 200, data

    @webapi_login_required
    def create(self, request, api_format, *args, **kwargs):
        """Handles HTTP POST requests to list resources.

        This is used to create a new object on the list, given the
        data provided in the request. It should usually return
        HTTP 201 Created upon success.

        By default, this returns HTTP 405 Method Not Allowed.
        """
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    def update(self, request, api_format, *args, **kwargs):
        """Handles HTTP PUT requests to object resources.

        This is used to update an object, given full or partial data provided
        in the request. It should usually return HTTP 200 OK upon success.

        By default, this returns HTTP 405 Method Not Allowed.
        """
        return HttpResponseNotAllowed(self.allowed_methods)

    @webapi_login_required
    @webapi_response_errors(DOES_NOT_EXIST, NOT_LOGGED_IN, PERMISSION_DENIED)
    def delete(self, request, api_format, *args, **kwargs):
        """Handles HTTP DELETE requests to object resources.

        This is used to delete an object, if the user has permissions to
        do so.

        By default, this deletes the object and returns HTTP 204 No Content.
        """
        if not self.model or self.uri_object_key is None:
            return HttpResponseNotAllowed(self.allowed_methods)

        try:
            obj = self.get_object(request, *args, **kwargs)
        except ObjectDoesNotExist:
            return DOES_NOT_EXIST

        if not self.has_delete_permissions(request, obj, *args, **kwargs):
            return self.get_no_access_error(request, obj=obj, *args, **kwargs)

        obj.delete()

        return 204, {}

    def get_queryset(self, request, is_list=False, *args, **kwargs):
        """Returns a queryset used for querying objects or lists of objects.

        Throws django.core.exceptions.ObjectDoesNotExist if the requested
        object does not exist.

        This can be overridden to filter the object list, such as for hiding
        non-public objects.

        The ``is_list`` parameter can be used to specialize the query based
        on whether an individual object or a list of objects is being queried.
        """
        return self.model.objects.all()

    def get_url_patterns(self):
        """Returns the Django URL patterns for this object and its children.

        This is used to automatically build up the URL hierarchy for all
        objects. Projects should call this for top-level resources and
        return them in the ``urls.py`` files.
        """
        urlpatterns = never_cache_patterns(
            '',
            url(r'^$', self, name=self._build_named_url(self.name_plural)),
        )

        for resource in self.list_child_resources:
            resource._parent_resource = self
            child_regex = r'^' + resource.uri_name + r'/'
            urlpatterns += patterns(
                '',
                url(child_regex, include(resource.get_url_patterns())),
            )

        if self.uri_object_key or self.singleton:
            # If the resource has particular items in it...
            if self.uri_object_key:
                base_regex = r'^(?P<%s>%s)/' % (self.uri_object_key,
                                                self.uri_object_key_regex)
            elif self.singleton:
                base_regex = r'^'

            urlpatterns += never_cache_patterns(
                '',
                url(base_regex + r'$', self,
                    name=self._build_named_url(self.name))
            )

            for resource in self.item_child_resources:
                resource._parent_resource = self
                child_regex = base_regex + resource.uri_name + r'/'
                urlpatterns += patterns(
                    '',
                    url(child_regex, include(resource.get_url_patterns())),
                )

        return urlpatterns

    def has_access_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user has read access to this object."""
        return True

    def has_list_access_permissions(self, request, *args, **kwargs):
        """Returns whether or not the user has read access to this list."""
        if self._parent_resource and self.model_parent_key:
            try:
                parent_obj = self._parent_resource.get_object(
                    request, *args, **kwargs)

                return self._parent_resource.has_access_permissions(
                    request, parent_obj, *args, **kwargs)
            except:
                # Other errors, like Does Not Exist, should be caught
                # separately. As of here, we'll allow it to pass, so that
                # the error isn't a Permission Denied when it should be
                # a Does Not Exist.
                pass

        return True

    def has_modify_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user can modify this object."""
        return False

    def has_delete_permissions(self, request, obj, *args, **kwargs):
        """Returns whether or not the user can delete this object."""
        return False

    def serialize_object(self, obj, *args, **kwargs):
        """Serializes the object into a Python dictionary."""
        request = kwargs.get('request', None)

        if request:
            if not hasattr(request, '_djblets_webapi_serialize_cache'):
                request._djblets_webapi_serialize_cache = {}

            if obj in request._djblets_webapi_serialize_cache:
                return self._clone_serialized_object(
                    request._djblets_webapi_serialize_cache[obj])

        data = {
            'links': self.get_links(self.item_child_resources, obj,
                                    *args, **kwargs),
        }

        if hasattr(request, '_djblets_webapi_expanded_resources'):
            expanded_resources = request._djblets_webapi_expanded_resources
        else:
            expand = request.GET.get('expand', request.POST.get('expand', ''))
            expanded_resources = expand.split(',')
            request._djblets_webapi_expanded_resources = expanded_resources

        # Make a copy of the list of expanded resources. We'll be temporarily
        # removing items as we recurse down into any nested objects, to
        # prevent infinite loops. We'll want to make sure we don't
        # permanently remove these entries, or subsequent list items will
        # be affected.
        orig_expanded_resources = list(expanded_resources)

        for field in six.iterkeys(self.fields):
            serialize_func = getattr(self, "serialize_%s_field" % field, None)

            if serialize_func and six.callable(serialize_func):
                value = serialize_func(obj, request=request)
            else:
                value = getattr(obj, field)

                if isinstance(value, models.Manager):
                    value = value.all()
                elif isinstance(value, models.ForeignKey):
                    value = value.get()

            expand_field = field in expanded_resources

            # Make sure that any given field expansion only applies once. This
            # prevents infinite recursion in the case where there's a loop in
            # the object graph.
            #
            # We'll be restoring these values once we're done serializing
            # objects.
            if expand_field:
                request._djblets_webapi_expanded_resources.remove(field)

            if isinstance(value, models.Model) and not expand_field:
                resource = self.get_serializer_for_object(value)
                assert resource

                data['links'][field] = {
                    'method': 'GET',
                    'href': resource.get_href(value, *args, **kwargs),
                    'title': six.text_type(value),
                }
            elif isinstance(value, QuerySet) and not expand_field:
                data[field] = [
                    {
                        'method': 'GET',
                        'href': self.get_serializer_for_object(o).get_href(
                            o, *args, **kwargs),
                        'title': six.text_type(o),
                    }
                    for o in value
                ]
            elif isinstance(value, QuerySet):
                data[field] = list(value)
            else:
                data[field] = value

        for resource_name in expanded_resources:
            if resource_name not in data['links']:
                continue

            # Try to find the resource from the child list.
            found = False

            for resource in self.item_child_resources:
                if resource_name in [resource.name, resource.name_plural]:
                    found = True
                    break

            if not found or not resource.model:
                continue

            del data['links'][resource_name]

            extra_kwargs = {
                self.uri_object_key: getattr(obj, self.model_object_key),
            }
            extra_kwargs.update(**kwargs)
            extra_kwargs.update(self.get_href_parent_ids(obj, **kwargs))

            data[resource_name] = resource._get_queryset(
                is_list=True, *args, **extra_kwargs)

        # Now that we're done serializing, restore the list of expanded
        # resource for the next call.
        request._djblets_webapi_expanded_resources = orig_expanded_resources

        if request:
            request._djblets_webapi_serialize_cache[obj] = \
                self._clone_serialized_object(data)

        return data

    def get_serializer_for_object(self, obj):
        """Returns the serializer used to serialize an object.

        This is called when serializing objects for payloads returned
        by this resource instance. It must return the resource instance
        that will be responsible for serializing the given object for the
        payload.

        By default, this calls ``get_resource_for_object`` to find the
        appropriate resource.
        """
        return get_resource_for_object(obj)

    def get_links(self, resources=[], obj=None, request=None,
                  *args, **kwargs):
        """Returns a dictionary of links coming off this resource.

        The resulting links will point to the resources passed in
        ``resources``, and will also provide special resources for
        ``self`` (which points back to the official location for this
        resource) and one per HTTP method/operation allowed on this
        resource.
        """
        links = {}
        base_href = None

        if obj:
            base_href = self.get_href(obj, request, *args, **kwargs)

        if not base_href:
            # We may have received None from the URL above.
            if request:
                base_href = request.build_absolute_uri()
            else:
                base_href = ''

        links['self'] = {
            'method': 'GET',
            'href': base_href,
        }

        # base_href without any query arguments.
        i = base_href.find('?')

        if i != -1:
            clean_base_href = base_href[:i]
        else:
            clean_base_href = base_href

        if 'POST' in self.allowed_methods and not obj:
            links['create'] = {
                'method': 'POST',
                'href': clean_base_href,
            }

        if 'PUT' in self.allowed_methods and obj:
            links['update'] = {
                'method': 'PUT',
                'href': clean_base_href,
            }

        if 'DELETE' in self.allowed_methods and obj:
            links['delete'] = {
                'method': 'DELETE',
                'href': clean_base_href,
            }

        for resource in resources:
            links[resource.link_name] = {
                'method': 'GET',
                'href': '%s%s/' % (clean_base_href, resource.uri_name),
            }

        for key, info in six.iteritems(
                self.get_related_links(obj, request, *args, **kwargs)):
            links[key] = {
                'method': info['method'],
                'href': info['href'],
            }

            if 'title' in info:
                links[key]['title'] = info['title']

        return links

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        """Returns links related to this resource.

        The result should be a dictionary of link names to a dictionary of
        information. The information should contain:

        * 'method' - The HTTP method
        * 'href' - The URL
        * 'title' - The title of the link (optional)
        * 'resource' - The WebAPIResource instance
        * 'list-resource' - True if this links to a list resource (optional)
        """
        return {}

    def get_href(self, obj, request, *args, **kwargs):
        """Returns the URL for this object."""
        if not self.uri_object_key:
            return None

        href_kwargs = {
            self.uri_object_key: getattr(obj, self.model_object_key),
        }
        href_kwargs.update(self.get_href_parent_ids(obj, **kwargs))

        return request.build_absolute_uri(
            reverse(self._build_named_url(self.name), kwargs=href_kwargs))

    def get_href_parent_ids(self, obj, **kwargs):
        """Returns a dictionary mapping parent object keys to their values for
        an object.
        """
        parent_ids = {}

        if self._parent_resource and self.model_parent_key:
            parent_obj = self.get_parent_object(obj)
            parent_ids = self._parent_resource.get_href_parent_ids(
                parent_obj, **kwargs)

            if self._parent_resource.uri_object_key:
                parent_ids[self._parent_resource.uri_object_key] = \
                    getattr(parent_obj, self._parent_resource.model_object_key)

        return parent_ids

    def get_parent_object(self, obj):
        """Returns the parent of an object.

        By default, this uses ``model_parent_key`` to figure out the parent,
        but it can be overridden for more complex behavior.
        """
        parent_obj = getattr(obj, self.model_parent_key)

        if isinstance(parent_obj, (models.Manager, models.ForeignKey)):
            parent_obj = parent_obj.get()

        return parent_obj

    def get_last_modified(self, request, obj):
        """Returns the last modified timestamp of an object.

        By default, this uses ``last_modified_field`` to determine what
        field in the model represents the last modified timestamp of
        the object.

        This can be overridden for more complex behavior.
        """
        if self.last_modified_field:
            return getattr(obj, self.last_modified_field)

        return None

    def get_etag(self, request, obj, *args, **kwargs):
        """Returns the ETag representing the state of the object.

        By default, this uses ``etag_field`` to determine what field in
        the model is unique enough to represent the state of the object.

        This can be overridden for more complex behavior. Any overridden
        functions should make sure to pass the result through
        ``encode_etag`` before returning a value.
        """
        if self.etag_field:
            etag = six.text_type(getattr(obj, self.etag_field))
        elif self.autogenerate_etags:
            etag = self.generate_etag(obj, self.fields, request=request,
                                      encode_etag=False, **kwargs)
        else:
            etag = None

        if etag:
            etag = self.encode_etag(request, etag)

        return etag

    def encode_etag(self, request, etag, *args, **kwargs):
        """Encodes an ETag for usage in a header.

        This will take a precomputed ETag, augment it with additional
        information, encode it as a SHA1, and return it.
        """
        return encode_etag('%s:%s' % (request.user.username, etag))

    def generate_etag(self, obj, fields, request, encode_etag=True, **kwargs):
        """Generates an ETag from the serialized values of all given fields.

        When called by legacy code, the resulting ETag will be encoded.
        All consumers are expected to update their get_etag() methods to
        call encode_etag() directly, and to pass encode_etag=False to this
        function.

        In a future version, the encode_etag parameter will go away, and
        this function's behavior will change to not return encoded ETags.
        """
        etag = repr(self.serialize_object(obj, request=request, **kwargs))

        # In Djblets 0.8.15, the responsibility for encoding moved to
        # get_etag(). However, legacy callers may end up calling
        # generate_etag, expecting the result to be encoded. In this case,
        # we want to perform the encoding and warn about deprecation.
        #
        # Future versions of Djblets will remove the encode_etag argument.
        if encode_etag:
            warnings.warn('WebAPIResource.generate_etag will stop generating '
                          'encoded ETags in 0.9.x. Update your get_etag() '
                          'method to pass encode_etag=False to this function '
                          'and to call encode_etag() on the result instead.',
                          DeprecationWarning)
            etag = self.encode_etag(request, etag)

        return etag

    def are_cache_headers_current(self, request, last_modified=None,
                                  etag=None):
        """Determines if cache headers from the client are current.

        This will compare the optionally-provided timestamp and ETag against
        any conditional cache headers sent by the client to determine if
        the headers are current. If they are, the caller can return
        HttpResponseNotModified instead of a payload.
        """
        return ((last_modified and
                 get_modified_since(request, last_modified)) or
                (etag and etag_if_none_match(request, etag)))

    def get_no_access_error(self, request, *args, **kwargs):
        """Returns an appropriate error when access is denied.

        By default, this will return PERMISSION_DENIED if the user is logged
        in, and NOT_LOGGED_IN if the user is anonymous.

        Subclasses can override this to return different or more detailed
        errors.
        """
        if request.user.is_authenticated():
            return PERMISSION_DENIED
        else:
            return NOT_LOGGED_IN

    def _build_named_url(self, name):
        """Builds a Django URL name from the provided name."""
        return '%s-resource' % name.replace('_', '-')

    def _get_queryset(self, request, is_list=False, *args, **kwargs):
        """Returns an optimized queryset.

        This calls out to the resource's get_queryset(), and then performs
        some optimizations to better fetch related objects, reducing future
        lookups in this request.
        """
        queryset = self.get_queryset(request, is_list=is_list, *args, **kwargs)

        if not hasattr(self, '_select_related_fields'):
            self._select_related_fields = []

            for field in six.iterkeys(self.fields):
                if hasattr(self, 'serialize_%s_field' % field):
                    continue

                field_type = getattr(self.model, field, None)

                if (field_type and
                    isinstance(field_type,
                               ReverseSingleRelatedObjectDescriptor)):
                    self._select_related_fields.append(field)

        if self._select_related_fields:
            queryset = \
                queryset.select_related(*self._select_related_fields)

        if is_list:
            if not hasattr(self, '_prefetch_related_fields'):
                self._prefetch_related_fields = []

                for field in six.iterkeys(self.fields):
                    if hasattr(self, 'serialize_%s_field' % field):
                        continue

                    field_type = getattr(self.model, field, None)

                    if (field_type and
                        isinstance(field_type,
                                   (ReverseManyRelatedObjectsDescriptor,
                                    ManyRelatedObjectsDescriptor))):
                        self._prefetch_related_fields.append(field)

            if self._prefetch_related_fields:
                queryset = \
                    queryset.prefetch_related(*self._prefetch_related_fields)

        return queryset

    def _clone_serialized_object(self, obj):
        """Clone a serialized object, for storing in the cache.

        This works similarly to deepcopy(), but is smart enough to only
        copy primitive types (dictionaries, lists, etc.) and won't
        interfere with model instances.

        deepcopy() should be smart enough to do that, and is documented
        as being smart enough, but Django models provide some functions
        that cause deepcopy() to dig in further than it should, eventually
        breaking in some cases.

        If you want the job done right, do it yourself.
        """
        if isinstance(obj, dict):
            return dict(
                (key, self._clone_serialized_object(value))
                for key, value in six.iteritems(obj)
            )
        elif isinstance(obj, list):
            return [
                self._clone_serialized_object(value)
                for value in obj
            ]
        else:
            return obj


class RootResource(WebAPIResource):
    """The root of a resource tree.

    This is meant to be instantiated with a list of immediate child
    resources. The result of ``get_url_patterns`` should be included in
    a project's ``urls.py``.
    """
    name = 'root'
    singleton = True

    def __init__(self, child_resources=[], include_uri_templates=True):
        super(RootResource, self).__init__()
        self.list_child_resources = child_resources
        self._uri_templates = {}
        self._include_uri_templates = include_uri_templates

    def get_etag(self, request, obj, *args, **kwargs):
        return self.encode_etag(request, repr(obj))

    def get(self, request, *args, **kwargs):
        """
        Retrieves the list of top-level resources, and a list of
        :term:`URI templates` for accessing any resource in the tree.
        """
        data = self.serialize_root(request, *args, **kwargs)
        etag = self.get_etag(request, data)

        if self.are_cache_headers_current(request, etag=etag):
            return HttpResponseNotModified()

        return 200, data, {
            'ETag': etag,
        }

    def serialize_root(self, request, *args, **kwargs):
        """Serializes the contents of the root resource.

        By default, this just provides links and URI templates. Subclasses
        can override this to provide additional data, or to otherwise
        change the structure of the root resource.
        """
        data = {
            'links': self.get_links(self.list_child_resources,
                                    request=request, *args, **kwargs),
        }

        if self._include_uri_templates:
            data['uri_templates'] = self.get_uri_templates(request, *args,
                                                           **kwargs)

        return data

    def get_uri_templates(self, request, *args, **kwargs):
        """Returns all URI templates in the resource tree.

        REST APIs can be very chatty if a client wants to be well-behaved
        and crawl the resource tree asking for the links, instead of
        hard-coding the paths. The benefit is that they can keep from
        breaking when paths change. The downside is that it can take many
        HTTP requests to get the right resource.

        This list of all URI templates allows clients who know the resource
        name and the data they care about to simply plug them into the
        URI template instead of trying to crawl over the whole tree. This
        can make things far more efficient.
        """
        if not self._uri_templates:
            self._uri_templates = {}

        base_href = request.build_absolute_uri()
        if base_href not in self._uri_templates:
            templates = {}
            for name, href in self._walk_resources(self, base_href):
                templates[name] = href

            self._uri_templates[base_href] = templates

        return self._uri_templates[base_href]

    def _walk_resources(self, resource, list_href):
        yield resource.name_plural, list_href

        for child in resource.list_child_resources:
            child_href = list_href + child.uri_name + '/'

            for name, href in self._walk_resources(child, child_href):
                yield name, href

        if resource.uri_object_key:
            object_href = '%s{%s}/' % (list_href, resource.uri_object_key)

            yield resource.name, object_href

            for child in resource.item_child_resources:
                child_href = object_href + child.uri_name + '/'

                for name, href in self._walk_resources(child, child_href):
                    yield name, href

    def api_404_handler(self, request, api_format=None, *args, **kwargs):
        """Default handler at the end of the URL patterns.

        This returns an API 404, instead of a normal django 404."""
        return WebAPIResponseError(
            request,
            err=DOES_NOT_EXIST,
            api_format=api_format)

    def get_url_patterns(self):
        """Returns the Django URL patterns for this object and its children.

        This returns the same list as WebAPIResource.get_url_patterns, but also
        introduces a generic catch-all 404 handler which returns API errors
        instead of HTML.
        """
        urlpatterns = super(RootResource, self).get_url_patterns()
        urlpatterns += never_cache_patterns(
            '', url(r'.*', self.api_404_handler))
        return urlpatterns


class UserResource(WebAPIResource):
    """A default resource for representing a Django User model."""
    model = User
    fields = {
        'id': {
            'type': int,
            'description': 'The numeric ID of the user.',
        },
        'username': {
            'type': str,
            'description': "The user's username.",
        },
        'first_name': {
            'type': str,
            'description': "The user's first name.",
        },
        'last_name': {
            'type': str,
            'description': "The user's last name.",
        },
        'fullname': {
            'type': str,
            'description': "The user's full name (first and last).",
        },
        'email': {
            'type': str,
            'description': "The user's e-mail address",
        },
        'url': {
            'type': str,
            'description': "The URL to the user's page on the site. "
                           "This is deprecated and will be removed in a "
                           "future version.",
        },
    }

    uri_object_key = 'username'
    uri_object_key_regex = r'[A-Za-z0-9@\._\-\'\+]+'
    model_object_key = 'username'
    autogenerate_etags = True

    allowed_methods = ('GET',)

    def serialize_fullname_field(self, user, **kwargs):
        return user.get_full_name()

    def serialize_url_field(self, user, **kwargs):
        return user.get_absolute_url()

    def has_modify_permissions(self, request, user, *args, **kwargs):
        """Returns whether or not the user can modify this object."""
        return request.user.is_authenticated() and user.pk == request.user.pk

    @augment_method_from(WebAPIResource)
    def get_list(self, *args, **kwargs):
        """Retrieves the list of users on the site."""
        pass


class GroupResource(WebAPIResource):
    """A default resource for representing a Django Group model."""
    model = Group
    fields = ('id', 'name')

    uri_object_key = 'group_name'
    uri_object_key_regex = r'[A-Za-z0-9_\-]+'
    model_object_key = 'name'
    autogenerate_etags = True

    allowed_methods = ('GET',)


def register_resource_for_model(model, resource):
    """Registers a resource as the official location for a model.

    ``resource`` can be a callable function that takes an instance of
    ``model`` and returns a ``WebAPIResource``.
    """
    _model_to_resources[model] = resource


def unregister_resource_for_model(model):
    """Removes the official location for a model."""
    del _model_to_resources[model]


def get_resource_for_object(obj):
    """Returns the resource for an object."""
    resource = _model_to_resources.get(obj.__class__, None)

    if not isinstance(resource, WebAPIResource) and six.callable(resource):
        resource = resource(obj)

    return resource


def get_resource_from_name(name):
    """Returns the resource of the specified name."""
    return _name_to_resources.get(name, None)


def get_resource_from_class(klass):
    """Returns the resource with the specified resource class."""
    return _class_to_resources.get(klass, None)


def unregister_resource(resource):
    """Unregisters a resource from the caches."""
    del _name_to_resources[resource.name]
    del _name_to_resources[resource.name_plural]
    del _class_to_resources[resource.__class__]


user_resource = UserResource()
group_resource = GroupResource()

# These are good defaults, and will be overridden if another class calls
# register_resource_for_model on these models.
register_resource_for_model(User, user_resource)
register_resource_for_model(Group, group_resource)
