from __future__ import unicode_literals

from django.db.models import Q
from django.utils import six
from django.utils.encoding import force_unicode
from django.utils.six.moves.urllib.parse import quote as urllib_quote
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (SPECIAL_PARAMS,
                                       webapi_login_required,
                                       webapi_request_fields)
from djblets.webapi.errors import NOT_LOGGED_IN, PERMISSION_DENIED
from djblets.webapi.resources import WebAPIResource as DjbletsWebAPIResource

from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)


CUSTOM_MIMETYPE_BASE = 'application/vnd.reviewboard.org'
EXTRA_DATA_LEN = len('extra_data.')


class WebAPIResource(DjbletsWebAPIResource):
    """A specialization of the Djblets WebAPIResource for Review Board."""

    autogenerate_etags = True
    mimetype_vendor = 'reviewboard.org'

    def has_access_permissions(self, *args, **kwargs):
        # By default, raise an exception if this is called. Specific resources
        # will have to explicitly override this and opt-in to access.
        raise NotImplementedError(
            '%s must provide a has_access_permissions method'
            % self.__class__.__name__)

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsWebAPIResource)
    def get(self, *args, **kwargs):
        """Returns the serialized object for the resource.

        This will require login if anonymous access isn't enabled on the
        site.
        """
        pass

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_request_fields(
        optional=dict({
            'counts-only': {
                'type': bool,
                'description': 'If specified, a single ``count`` field is '
                               'returned with the number of results, instead '
                               'of the results themselves.',
            },
        }, **DjbletsWebAPIResource.get_list.optional_fields),
        required=DjbletsWebAPIResource.get_list.required_fields,
        allow_unknown=True
    )
    def get_list(self, request, *args, **kwargs):
        """Returns a list of objects.

        This will require login if anonymous access isn't enabled on the
        site.

        If ``?counts-only=1`` is passed on the URL, then this will return
        only a ``count`` field with the number of entries, instead of the
        serialized objects.
        """
        if self.model and request.GET.get('counts-only', False):
            return 200, {
                'count': self.get_queryset(request, is_list=True,
                                           *args, **kwargs).count()
            }
        else:
            return self._get_list_impl(request, *args, **kwargs)

    @webapi_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsWebAPIResource)
    def delete(self, *args, **kwargs):
        pass

    def _get_list_impl(self, request, *args, **kwargs):
        """Actual implementation to return the list of results.

        This by default calls the parent WebAPIResource.get_list, but this
        can be overridden by subclasses to provide a more custom
        implementation while still retaining the ?counts-only=1 functionality.
        """
        return super(WebAPIResource, self).get_list(request, *args, **kwargs)

    def get_href(self, obj, request, *args, **kwargs):
        """Returns the URL for this object.

        This is an override of get_href, which takes into account our
        local_site_name namespacing in order to get the right prefix on URLs.
        """
        if not self.uri_object_key:
            return None

        href_kwargs = {
            self.uri_object_key: getattr(obj, self.model_object_key),
        }
        href_kwargs.update(self.get_href_parent_ids(obj, **kwargs))

        return request.build_absolute_uri(
            self.get_item_url(request=request, **href_kwargs))

    def get_list_url(self, **kwargs):
        """Returns the URL to the list version of this resource.

        This will generate a URL for the resource, given the provided
        arguments for the URL pattern.
        """
        return self._get_resource_url(self.name_plural, **kwargs)

    def get_item_url(self, **kwargs):
        """Returns the URL to the item version of this resource.

        This will generate a URL for the resource, given the provided
        arguments for the URL pattern.
        """
        return self._get_resource_url(self.name, **kwargs)

    def build_queries_for_int_field(self, request, field_name,
                                    query_param_name=None):
        """Builds queries based on request parameters for an int field.

        get_queryset() implementations can use this to allow callers to
        filter results through range matches. Callers can search for exact
        matches, or can do <, <=, >, or >= matches.
        """
        if not query_param_name:
            query_param_name = field_name.replace('_', '-')

        q = Q()

        if query_param_name in request.GET:
            q = q & Q(**{field_name: request.GET[query_param_name]})

        for op in ('gt', 'gte', 'lt', 'lte'):
            param = '%s-%s' % (query_param_name, op)

            if param in request.GET:
                query_field = '%s__%s' % (field_name, op)
                q = q & Q(**{query_field: request.GET[param]})

        return q

    def can_import_extra_data_field(self, obj, field):
        """Returns whether a particular field in extra_data can be imported.

        Subclasses can use this to limit which fields are imported by
        import_extra_data. By default, all fields can be imported.
        """
        return True

    def _get_resource_url(self, name, local_site_name=None, request=None,
                          **kwargs):
        return local_site_reverse(
            self._build_named_url(name),
            local_site_name=local_site_name,
            request=request,
            kwargs=kwargs)

    def _get_local_site(self, local_site_name):
        if local_site_name:
            return LocalSite.objects.get(name=local_site_name)
        else:
            return None

    def _get_form_errors(self, form):
        fields = {}

        for field in form.errors:
            fields[field] = [force_unicode(e) for e in form.errors[field]]

        return fields

    def _no_access_error(self, user):
        """Returns a WebAPIError indicating the user has no access.

        Which error this returns depends on whether or not the user is logged
        in. If logged in, this will return _no_access_error(request.user).
        Otherwise, it will return NOT_LOGGED_IN.
        """
        if user.is_authenticated():
            return PERMISSION_DENIED
        else:
            return NOT_LOGGED_IN

    def import_extra_data(self, obj, extra_data, fields):
        for key, value in six.iteritems(fields):
            if key.startswith('extra_data.'):
                key = key[EXTRA_DATA_LEN:]

                if self.can_import_extra_data_field(obj, key):
                    if value != '':
                        if value in ('true', 'True', 'TRUE'):
                            value = True
                        elif value in ('false', 'False', 'FALSE'):
                            value = False
                        else:
                            try:
                                value = int(value)
                            except ValueError:
                                pass

                        extra_data[key] = value
                    elif key in extra_data:
                        del extra_data[key]

    def _build_redirect_with_args(self, request, new_url):
        """Builds a redirect URL with existing query string arguments.

        This will construct a URL that contains all the query string arguments
        provided in this request.

        This will not include the special arguments handled by the base
        WebAPIResource in Djblets. Those will be specially added
        automatically, so there's no need to do this twice here.
        """
        query_str = '&'.join([
            '%s=%s' % (urllib_quote(key), urllib_quote(value))
            for key, value in six.iteritems(request.GET)
            if key not in SPECIAL_PARAMS
        ])

        if '?' in new_url:
            new_url += '&' + query_str
        else:
            new_url += '?' + query_str

        return new_url
