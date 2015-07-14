from __future__ import unicode_literals

from django.contrib.auth.models import User
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.resources import ExtensionResource
from djblets.webapi.resources.registry import (ResourcesRegistry,
                                               register_resource_for_model)

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.extensions.base import get_extension_manager
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.notifications.models import WebHookTarget
from reviewboard.reviews.models import (Comment, DefaultReviewer,
                                        Group, ReviewRequest,
                                        ReviewRequestDraft, Review,
                                        ScreenshotComment, Screenshot,
                                        FileAttachmentComment)
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.base import WebAPIResource
from reviewboard.webapi.models import WebAPIToken


class Resources(ResourcesRegistry):
    """Manages the instances for all API resources.

    This handles dynamically loading API resource instances upon request,
    and registering those resources with models.

    When accessing a resource through this class for the first time, it will
    be imported from the proper file and cached. Subsequent requests will be
    returned from the cache.
    """

    resource_search_path = [
        'reviewboard.webapi.resources',
    ]

    def __init__(self):
        super(Resources, self).__init__()

        self.extension = ExtensionResource(get_extension_manager())

    def register_resources(self):
        """Register all the resource model associations."""
        register_resource_for_model(ChangeDescription, self.change)
        register_resource_for_model(
            Comment,
            lambda obj: (obj.review.get().is_reply() and
                         self.review_reply_diff_comment or
                         self.review_diff_comment))
        register_resource_for_model(DefaultReviewer, self.default_reviewer)
        register_resource_for_model(
            DiffSet,
            lambda obj: obj.history_id and self.diff or self.draft_diff)
        register_resource_for_model(
            FileDiff,
            lambda obj: (obj.diffset.history_id and
                         self.filediff or
                         self.draft_filediff))
        register_resource_for_model(Group, self.review_group)
        register_resource_for_model(RegisteredExtension, self.extension)
        register_resource_for_model(HostingServiceAccount,
                                    self.hosting_service_account)
        register_resource_for_model(Repository, self.repository)
        register_resource_for_model(
            Review,
            lambda obj: obj.is_reply() and self.review_reply or self.review)
        register_resource_for_model(ReviewRequest, self.review_request)
        register_resource_for_model(ReviewRequestDraft,
                                    self.review_request_draft)
        register_resource_for_model(Screenshot, self.screenshot)
        register_resource_for_model(FileAttachment, self.file_attachment)
        register_resource_for_model(
            FileAttachment,
            lambda obj: (obj.is_from_diff and
                         self.diff_file_attachment or
                         self.file_attachment))
        register_resource_for_model(
            ScreenshotComment,
            lambda obj: (obj.review.get().is_reply() and
                         self.review_reply_screenshot_comment or
                         self.review_screenshot_comment))
        register_resource_for_model(
            FileAttachmentComment,
            lambda obj: (obj.review.get().is_reply() and
                         self.review_reply_file_attachment_comment or
                         self.review_file_attachment_comment))
        register_resource_for_model(User, self.user)
        register_resource_for_model(WebAPIToken, self.api_token)
        register_resource_for_model(WebHookTarget, self.webhook)


resources = Resources()


__all__ = ['Resources', 'resources', 'WebAPIResource']
