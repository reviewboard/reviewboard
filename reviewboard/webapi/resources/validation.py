from djblets.util.decorators import augment_method_from
from djblets.webapi.resources import RootResource as DjbletsRootResource

from reviewboard.webapi.resources import resources


class ValidationResource(DjbletsRootResource):
    """Links to validation resources."""
    name = 'validation'

    def __init__(self, *args, **kwargs):
        super(ValidationResource, self).__init__([
            resources.validate_diff,
        ], include_uri_templates=False, *args, **kwargs)

    @augment_method_from(DjbletsRootResource)
    def get(self, request, *args, **kwargs):
        """Retrieves links to all the validation resources."""
        pass


validation_resource = ValidationResource()
