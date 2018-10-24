from __future__ import unicode_literals

from django.http import Http404
from djblets.webapi.decorators import (webapi_response_errors,
                                       webapi_request_fields)
from djblets.webapi.errors import DOES_NOT_EXIST
from djblets.webapi.fields import IntFieldType, StringFieldType

from reviewboard.reviews.views import ReviewsDiffViewerView
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.decorators import (webapi_check_local_site,
                                           webapi_check_login_required)
from reviewboard.webapi.resources import resources


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
    added_in = '2.0'

    name = 'diff_context'
    singleton = True

    @webapi_check_login_required
    @webapi_check_local_site
    @webapi_request_fields(
        optional={
            'revision': {
                'type': IntFieldType,
                'description': 'Which revision of the diff to show.',
            },
            'filenames': {
                'type': StringFieldType,
                'description': 'A list of case-sensitive filenames or Unix '
                               'shell patterns used to filter the resulting '
                               'list of files.',
                'added_in': '3.0.4',
            },
            'interdiff-revision': {
                'type': IntFieldType,
                'description': 'A tip revision for showing interdiffs. If '
                               'this is provided, the ``revision`` field will '
                               'be the base diff.',
                'added_in': '2.0.7',
            },
            'page': {
                'type': IntFieldType,
                'description': 'The page number for paginated diffs.',
            },
            'base-commit-id': {
                'type': IntFieldType,
                'description': (
                    'The ID of the base commit to use to generate the diff '
                    'for review requests created with commit history.\n'
                    '\n'
                    'Only changes from after the specified commit will be '
                    'included in the diff.'
                ),
            },
            'tip-commit-id': {
                'type': IntFieldType,
                'description': (
                    'The ID of the tip commit to use to generate the diff '
                    'for review requests created with commit history.\n'
                    '\n'
                    'No changes from beyond this commit will be included in '
                    'the diff.'
                ),
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

        review_request = resources.review_request.get_object(
            request, review_request_id=review_request_id,
            local_site_name=local_site_name, *args, **kwargs)

        if not review_request.is_accessible_by(request.user):
            return self.get_no_access_error(request, obj=review_request, *args,
                                            **kwargs)

        try:
            view = DiffViewerContextView.as_view()
            context = view(request=request,
                           review_request_id=review_request_id,
                           revision=revision,
                           interdiff_revision=interdiff_revision,
                           local_site_name=local_site_name)
        except Http404:
            return DOES_NOT_EXIST

        return 200, {
            self.item_result_key: context['diff_context'],
        }


diff_context_resource = DiffContextResource()
