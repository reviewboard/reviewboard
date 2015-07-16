from __future__ import unicode_literals

from django.utils import six
from django.utils.encoding import force_unicode
from django.utils.six.moves.urllib.parse import quote as urllib_quote
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import (SPECIAL_PARAMS,
                                       webapi_login_required,
                                       webapi_request_fields)
from djblets.webapi.resources.base import \
    WebAPIResource as DjbletsWebAPIResource
from djblets.webapi.resources.mixins.api_tokens import ResourceAPITokenMixin
from djblets.webapi.resources.mixins.queries import APIQueryUtilsMixin

from reviewboard.site.models import LocalSite
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.models import WebAPIToken


CUSTOM_MIMETYPE_BASE = 'application/vnd.reviewboard.org'
EXTRA_DATA_LEN = len('extra_data.')


class WebAPIResource(ResourceAPITokenMixin, APIQueryUtilsMixin,
                     DjbletsWebAPIResource):
    """A specialization of the Djblets WebAPIResource for Review Board."""

    autogenerate_etags = True
    mimetype_vendor = 'reviewboard.org'
    api_token_model = WebAPIToken

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

    def can_import_extra_data_field(self, obj, field):
        """Returns whether a particular field in extra_data can be imported.

        Subclasses can use this to limit which fields are imported by
        import_extra_data. By default, all fields can be imported.
        """
        return True

    def build_resource_url(self, name, local_site_name=None, request=None,
                           **kwargs):
        """Build the URL to a resource, factoring in Local Sites.

        Args:
            name (unicode):
                The resource name.

            local_site_name (unicode):
                The LocalSite name.

            request (django.http.HttpRequest):
                The HTTP request from the client.

            kwargs (dict):
                The keyword arguments needed for URL resolution.

        Returns:
            unicode: The resulting absolute URL to the resource.
        """
        url = local_site_reverse(
            self._build_named_url(name),
            local_site_name=local_site_name,
            request=request,
            kwargs=kwargs)

        if request:
            return request.build_absolute_uri(url)

        return url

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
