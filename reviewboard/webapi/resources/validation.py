from djblets.util.decorators import augment_method_from
from djblets.webapi.resources.root import RootResource as DjbletsRootResource

from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.base import RBResourceMixin
from reviewboard.webapi.resources import resources


class ValidationResource(RBResourceMixin, DjbletsRootResource):
    """Links to validation resources."""
    added_in = '2.0'

    name = 'validation'

    def __init__(self, *args, **kwargs):
        super(ValidationResource, self).__init__([
            resources.validate_diff,
            resources.validate_diffcommit,
        ], include_uri_templates=False, *args, **kwargs)

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsRootResource)
    def get(self, request, *args, **kwargs):
        """Retrieves links to all the validation resources."""
        pass


validation_resource = ValidationResource()
