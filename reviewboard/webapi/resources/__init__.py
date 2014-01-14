from __future__ import unicode_literals

import logging

from django.contrib.auth.models import User
from djblets.extensions.models import RegisteredExtension
from djblets.extensions.resources import ExtensionResource
from djblets.webapi.resources import register_resource_for_model

from reviewboard.attachments.models import FileAttachment
from reviewboard.diffviewer.models import DiffSet, FileDiff
from reviewboard.changedescs.models import ChangeDescription
from reviewboard.extensions.base import get_extension_manager
from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.reviews.models import (Comment, DefaultReviewer,
                                        Group, ReviewRequest,
                                        ReviewRequestDraft, Review,
                                        ScreenshotComment, Screenshot,
                                        FileAttachmentComment)
from reviewboard.scmtools.models import Repository
from reviewboard.webapi.base import WebAPIResource


class Resources(object):
    """Manages the instances for all API resources.

    This handles dynamically loading API resource instances upon request,
    and registering those resources with models.

    When accessing a resource through this class for the first time, it will
    be imported from the proper file and cached. Subsequent requests will be
    returned from the cache.
    """
    def __init__(self):
        self.extension = ExtensionResource(get_extension_manager())

        self._loaded = False

    def __getattr__(self, name):
        """Returns a resource instance as an attribute.

        If the resource hasn't yet been loaded into cache, it will be
        imported, fetched from the module, and cached. Subsequent attribute
        fetches for this resource will be returned from the cache.
        """
        if not self._loaded:
            self._loaded = True
            self._register_resources()

        if name not in self.__dict__:
            instance_name = '%s_resource' % name

            try:
                mod = __import__('reviewboard.webapi.resources.%s' % name,
                                 {}, {}, [instance_name])
                self.__dict__[name] = getattr(mod, instance_name)
            except (ImportError, AttributeError) as e:
                logging.error('Unable to load webapi resource %s: %s'
                              % (name, e))
                raise AttributeError('%s is not a valid resource name' % name)

        return self.__dict__[name]

    def _register_resources(self):
        """Registers all the resource model associations."""
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


resources = Resources()


__all__ = ['Resources', 'resources', 'WebAPIResource']
