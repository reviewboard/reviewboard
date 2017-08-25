"""Review Board's extension resource."""

from djblets.extensions.resources import (
    ExtensionResource as DjbletsExtensionResource)
from djblets.util.decorators import augment_method_from

from reviewboard.extensions.base import get_extension_manager
from reviewboard.webapi.base import RBResourceMixin
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)


class ExtensionResource(RBResourceMixin, DjbletsExtensionResource):
    """Review Board's extension resource.

    This resource special-cases the one in Djblets to provide API token and
    OAuth token access.
    """

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsExtensionResource)
    def get(self, *args, **kwargs):
        pass


extension_resource = ExtensionResource(get_extension_manager())
