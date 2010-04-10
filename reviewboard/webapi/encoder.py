from django.contrib.auth.models import User
from django.template.defaultfilters import timesince
from djblets.webapi.core import WebAPIEncoder
from djblets.webapi.resources import userResource

from reviewboard.diffviewer.models import FileDiff, DiffSet
from reviewboard.reviews.models import ReviewRequest, Review, Group, Comment, \
                                       ReviewRequestDraft, Screenshot, \
                                       ScreenshotComment
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.json import status_to_string
from reviewboard.webapi.resources import diffSetResource, \
                                         fileDiffResource, \
                                         repositoryResource, \
                                         reviewCommentResource, \
                                         reviewDraftResource, \
                                         reviewGroupResource, \
                                         reviewRequestResource, \
                                         reviewRequestDraftResource, \
                                         reviewResource, \
                                         reviewReplyResource, \
                                         screenshotResource, \
                                         screenshotCommentResource


class ReviewBoardAPIEncoder(WebAPIEncoder):
    def encode(self, o, api_format, *args, **kwargs):
        resource = None

        if isinstance(o, Group):
            resource = reviewGroupResource
        elif isinstance(o, User):
            resource = userResource
        elif isinstance(o, ReviewRequest):
            resource = reviewRequestResource
        elif isinstance(o, ReviewRequestDraft):
            resource = reviewRequestDraftResource
        elif isinstance(o, Review):
            if o.is_reply():
                resource = reviewReplyResource
            else:
                resource = reviewResource
        elif isinstance(o, Comment):
            resource = reviewCommentResource
        elif isinstance(o, ScreenshotComment):
            resource = screenshotCommentResource
        elif isinstance(o, Screenshot):
            resource = screenshotResource
        elif isinstance(o, FileDiff):
            resource = fileDiffResource
        elif isinstance(o, DiffSet):
            resource = diffSetResource
        elif isinstance(o, Repository):
            resource = repositoryResource
        else:
            return super(ReviewBoardAPIEncoder, self).encode(
                o, api_format=api_format, *args, **kwargs)

        return resource.serialize_object(o, api_format=api_format)
