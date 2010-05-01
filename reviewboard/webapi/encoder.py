from django.contrib.auth.models import User
from django.template.defaultfilters import timesince
from djblets.webapi.core import WebAPIEncoder
from djblets.webapi.resources import user_resource

from reviewboard.diffviewer.models import FileDiff, DiffSet
from reviewboard.reviews.models import ReviewRequest, Review, Group, Comment, \
                                       ReviewRequestDraft, Screenshot, \
                                       ScreenshotComment
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.json import status_to_string
from reviewboard.webapi.resources import diffset_resource, \
                                         filediff_resource, \
                                         repository_resource, \
                                         review_comment_resource, \
                                         review_group_resource, \
                                         review_request_resource, \
                                         review_request_draft_resource, \
                                         review_resource, \
                                         review_reply_resource, \
                                         review_screenshot_comment_resource, \
                                         screenshot_resource


class ReviewBoardAPIEncoder(WebAPIEncoder):
    def encode(self, o, *args, **kwargs):
        resource = None

        if isinstance(o, Group):
            resource = review_group_resource
        elif isinstance(o, User):
            resource = user_resource
        elif isinstance(o, ReviewRequest):
            resource = review_request_resource
        elif isinstance(o, ReviewRequestDraft):
            resource = review_request_draft_resource
        elif isinstance(o, Review):
            if o.is_reply():
                resource = review_reply_resource
            else:
                resource = review_resource
        elif isinstance(o, Comment):
            resource = review_comment_resource
        elif isinstance(o, ScreenshotComment):
            resource = review_screenshot_comment_resource
        elif isinstance(o, Screenshot):
            resource = screenshot_resource
        elif isinstance(o, FileDiff):
            resource = filediff_resource
        elif isinstance(o, DiffSet):
            resource = diffset_resource
        elif isinstance(o, Repository):
            resource = repository_resource
        else:
            return super(ReviewBoardAPIEncoder, self).encode(
                o, *args, **kwargs)

        return resource.serialize_object(o, *args, **kwargs)
