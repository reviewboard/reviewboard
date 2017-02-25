from __future__ import unicode_literals

from django.contrib.auth import logout
from django.utils import six
from djblets.webapi.decorators import webapi_login_required
from djblets.webapi.resources.registry import get_resource_for_object

from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)


class SessionResource(WebAPIResource):
    """Information on the active user's session.

    This includes information on the user currently logged in through the
    calling client, if any. Currently, the resource links to that user's
    own resource, making it easy to figure out the user's information and
    any useful related resources.
    """
    name = 'session'
    singleton = True
    allowed_methods = ('GET', 'DELETE')

    @webapi_check_local_site
    @webapi_check_login_required
    def get(self, request, *args, **kwargs):
        """Returns information on the client's session.

        This currently just contains information on the currently logged-in
        user (if any).
        """
        expanded_resources = request.GET.get('expand', '').split(',')

        authenticated = request.user.is_authenticated()

        data = {
            'authenticated': authenticated,
            'links': self.get_links(request=request, *args, **kwargs),
        }

        if authenticated and 'user' in expanded_resources:
            data['user'] = request.user
            del data['links']['user']

        return 200, {
            self.name: data,
        }

    @webapi_check_local_site
    @webapi_login_required
    def delete(self, request, *args, **kwargs):
        """Clears the user's client session and the session cookie.

        This is equivalent to logging out a user. The existing session cookie
        will be invalidated and will no longer be accepted.

        This will return a :http:`204`.
        """
        logout(request)

        return 204, {}

    def get_related_links(self, obj=None, request=None, *args, **kwargs):
        links = {}

        if request and request.user.is_authenticated():
            user_resource = get_resource_for_object(request.user)
            href = user_resource.get_href(request.user, request,
                                          *args, **kwargs)

            # Since there's no object, DELETE won't be populated automatically.
            clean_href = request.build_absolute_uri()
            i = clean_href.find('?')

            if i != -1:
                clean_href = clean_href[:i]

            links['delete'] = {
                'method': 'DELETE',
                'href': clean_href,
            }

            links['user'] = {
                'method': 'GET',
                'href': href,
                'title': six.text_type(request.user),
                'resource': user_resource,
                'list-resource': False,
            }

        return links


session_resource = SessionResource()
