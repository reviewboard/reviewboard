"""Root-level resource for querying reviews.

Version Added:
    5.0
"""

from django.db.models import Q
from djblets.util.decorators import augment_method_from
from djblets.webapi.decorators import webapi_request_fields
from djblets.webapi.fields import (BooleanFieldType,
                                   DateTimeFieldType,
                                   StringFieldType)

from reviewboard.accounts.models import User
from reviewboard.reviews.models import Group, Review
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.decorators import webapi_check_local_site
from reviewboard.webapi.resources import resources
from reviewboard.webapi.resources.base_review import BaseReviewResource


class RootReviewResource(BaseReviewResource):
    """Provides information on reviews.

    This is a top level endpoint that allows you to list and query all
    reviews in the system.

    Version Added:
        5.0
    """

    added_in = '5.0'
    allowed_methods = ('GET', )
    model = Review
    uri_template_name = 'all_review'

    item_child_resources = [
        resources.review_diff_comment,
        resources.review_file_attachment_comment,
        resources.review_general_comment,
        resources.review_reply,
        resources.review_screenshot_comment,
    ]

    @webapi_check_local_site
    def get_queryset(self, request, is_list=False, *args, **kwargs):
        """Return a queryset for Review models.

        Args:
            request (django.http.HttpRequest):
                The HTTP request from the client.

            is_list (bool, unused):
                Whether or not the queryset is for listing results.

            *args (tuple):
                Additional positional arguments.

            **kwargs (dict):
                Additional keyword arguments.

        Returns:
            django.db.models.query.QuerySet:
            A queryset for Review models.
        """
        q = Q(**self.get_base_reply_to_field(*args, **kwargs))
        public = None

        if 'public' in request.GET:
            public = request.GET.get('public') in ('1', 'true', 'True')

        if 'user' in request.GET:
            user = list((
                User.objects
                .filter(username=request.GET.get('user'))
                .values_list('pk', flat=True)
            ))

            if user:
                q &= Q(user=user[0])
            else:
                return self.model.objects.none()

        if 'repository' in request.GET:
            repository = list((
                Repository.objects
                .filter(name=request.GET.get('repository'))
                .values_list('pk', flat=True)
            ))

            if repository:
                q &= Q(review_request__repository=repository[0])
            else:
                return self.model.objects.none()

        if 'last-updated-from' in request.GET:
            q &= Q(timestamp__gte=request.GET.get('last-updated-from'))

        if 'last-updated-to' in request.GET:
            q &= Q(timestamp__lt=request.GET.get('last-updated-to'))

        if 'review-group' in request.GET:
            users = list((
                Group.objects
                .filter(name=request.GET.get('review-group'))
                .values_list('users')
            ))
            q &= Q(user__in=users)

        return self.model.objects.accessible(request.user,
                                             extra_query=q,
                                             public=public,
                                             local_site=request.local_site)

    def get_base_reply_to_field(self, *args, **kwargs):
        """Return the base reply-to field for this resource.

        Args:
            *args (tuple, unused):
                Additional positional arguments.

            **kwargs (dict, unused):
                Additional keyword arguments.

        Returns:
            dict:
            A dictionary containing the base reply-to field.
        """
        return {
            'base_reply_to__isnull': True,
        }

    @webapi_check_local_site
    @webapi_request_fields(
        optional=dict({
            'last-updated-from': {
                'type': DateTimeFieldType,
                'description': "The earliest date/time the review could "
                               "be last updated. This is compared against "
                               "the review's ``timestamp`` field. This "
                               "must be a valid :term:`date/time format`.",
            },
            'last-updated-to': {
                'type': DateTimeFieldType,
                'description': "The date/time that the reviews must be "
                               "last updated before. This is compared against "
                               "the review\'s ``timestamp`` field. This "
                               "must be a valid :term:`date/time format`.",
            },
            'public': {
                'type': BooleanFieldType,
                'description': 'Whether to filter for public (published) '
                               'reviews. If not set, both published and '
                               'unpublished reviews will be included.',
            },
            'repository': {
                'type': StringFieldType,
                'description': 'The repository name that the review requests '
                               'of the reviews must be part of.',
            },
            'review-group': {
                'type': StringFieldType,
                'description': 'The group name of users that the reviews '
                               'must be owned by.',
            },
            'user': {
                'type': StringFieldType,
                'description': 'The username of the user that the reviews '
                               'must be owned by.',
            },
        }, **BaseReviewResource.get_list.optional_fields),
        required=BaseReviewResource.get_list.required_fields,
        allow_unknown=True
    )
    @augment_method_from(BaseReviewResource)
    def get_list(self, *args, **kwargs):
        """Return the list of reviews."""
        pass


root_review_resource = RootReviewResource()
