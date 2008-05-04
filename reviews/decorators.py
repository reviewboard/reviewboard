from django.http import Http404
from django.shortcuts import get_object_or_404

from djblets.util.decorators import simple_decorator

from reviewboard.reviews.models import ReviewRequest


def owner_required(perms=['reviews.change_reviewrequest'],
                   only_nonpublic=False):
    """
    Create a decorator for review_request views.
    Returned decorator modifies the original view to check if user is the
    submitter or has any specified permission for the review request.
    If not, raise Http404

    only_nonpublic : If this option is True, decorate only when the review is
                     not public.
    """
    @simple_decorator
    def deco(view_func):
        def _check(request, review_request_id, *args, **kwargs):
            def has_any_perm(user, perms):
                """Helper function. return true if user has any permission."""
                for perm in perms:
                    if user.has_perm(perm):
                        return True
                return False

            user = request.user
            review_request = get_object_or_404(ReviewRequest, pk=review_request_id)

            # If 'only_nonpublic' flag is set and the review_request is public,
            # no need to check.
            if (only_nonpublic and review_request.public) or \
               review_request.submitter == user or \
               has_any_perm(user, perms):
                return view_func(request, review_request_id, *args, **kwargs)
            else:
                raise Http404

        return _check
    return deco
