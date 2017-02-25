from __future__ import unicode_literals

from django.http import Http404
from djblets.webapi.decorators import (webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import DOES_NOT_EXIST

from reviewboard.reviews.views import ReviewsDiffViewerView
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)


class DiffViewerContextView(ReviewsDiffViewerView):
    # We piggy-back on the ReviewsDiffViewerView to do all the heavy
    # lifting. By overriding render_to_response, we don't have to render it
    # to HTML, and can just return the data that we need from javascript.
    def render_to_response(self, context, **kwargs):
        return context


class DiffContextResource(WebAPIResource):
    """Provides context information for a specific diff view.

    The output of this is more or less internal to the Review Board web UI.
    This will return the various pieces of information required to render a
    diff view for a given diff revision/interdiff. This is used to re-render
    the diff viewer without a reload when navigating between revisions.
    """
    # The javascript side of this is in DiffViewerPageModel and it's associated
    # sub-models.
    name = 'diff_context'
    singleton = True

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'revision': {
                'type': int,
                'description': 'Which revision of the diff to show.',
            },
            'interdiff-revision': {
                'type': int,
                'description': 'A tip revision for showing interdiffs. If '
                               'this is provided, the ``revision`` field will '
                               'be the base diff.',
            },
            'page': {
                'type': int,
                'description': 'The page number for paginated diffs.',
            },
        },
    )
    @webapi_response_errors(DOES_NOT_EXIST)
    def get(self, request, review_request_id, local_site_name=None,
            *args, **kwargs):
        """Returns the context info for a particular revision or interdiff.

        The output of this is more or less internal to the Review Board web UI.
        The result will be an object with several fields for the files in the
        diff, pagination information, and other data which is used to render
        the diff viewer page.

        Note that in versions 2.0.0 through 2.0.6, the ``interdiff-revision``
        parameter was named ``interdiff_revision``. Because of the internal
        nature of this API, this was changed without adding backwards
        compatibility for 2.0.7.
        """
        revision = request.GET.get('revision')
        interdiff_revision = request.GET.get('interdiff-revision')

        try:
            view = DiffViewerContextView.as_view()
            context = view(request, local_site_name, review_request_id,
                           revision, interdiff_revision)
        except Http404:
            return DOES_NOT_EXIST

        return 200, {
            self.item_result_key: context['diff_context'],
        }


diff_context_resource = DiffContextResource()
