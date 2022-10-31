from djblets.util.decorators import augment_method_from
from djblets.webapi.resources.root import RootResource as DjbletsRootResource

from reviewboard.webapi.server_info import get_server_info
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.resources import WebAPIResource, resources


class RootResource(WebAPIResource, DjbletsRootResource):
    """Links to all the main resources, including URI templates to resources
    anywhere in the tree.

    This should be used as a starting point for any clients that need to access
    any resources in the API. By browsing through the resource tree instead of
    hard-coding paths, your client can remain compatible with any changes in
    the resource URI scheme.

    This also contains information on the server and the capabilities of
    the API. This information was formerly provided only by the Server Info
    resource, but has been moved here as a convenience to clients.
    """

    mimetype_vendor = 'reviewboard.org'

    def __init__(self, *args, **kwargs):
        super(RootResource, self).__init__([
            resources.default_reviewer,
            resources.extension,
            resources.hosting_service,
            resources.hosting_service_account,
            resources.oauth_app,
            resources.oauth_token,
            resources.repository,
            resources.review_group,
            resources.review_request,
            resources.root_diff_comment,
            resources.root_file_attachment_comment,
            resources.root_general_comment,
            resources.root_review,
            resources.search,
            resources.server_info,
            resources.session,
            resources.user,
            resources.validation,
            resources.webhook,
        ], *args, **kwargs)

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsRootResource)
    def get(self, request, *args, **kwargs):
        """Retrieves the list of top-level resources and templates."""
        pass

    def get_uri_templates(self, request, *args, **kwargs):
        """Return all URI templates in the resource tree.

        Args:
            request (django.http.HttpRequest):
                The GET request for the Root resource.

            *args (tuple, unused):
                Additional unused arguments.

            **kwargs (dict, unused):
                Additional unused keyword arguments.

        Returns:
            dict:
            A mapping of resources to their URI templates.
        """
        # Manually include this resource to maintain compatibility with
        # our Python 2.7 API behavior. This is a bandaid for a larger
        # issue that stems from resources that share the same name but
        # have different URI templates.
        base_href = request.build_absolute_uri()
        self.register_uri_template(
            name='search',
            relative_path='%ssearch/{username}/' % base_href)

        return super().get_uri_templates(request, *args, **kwargs)

    def serialize_root(self, request, *args, **kwargs):
        root = super(RootResource, self).serialize_root(request, *args,
                                                        **kwargs)
        root.update(get_server_info(request))

        return root


root_resource = RootResource()
