from __future__ import unicode_literals

from reviewboard.hostingsvcs.models import HostingServiceAccount
from reviewboard.hostingsvcs.service import HostingService
from reviewboard.reviews.models import ReviewRequest
from reviewboard.scmtools.models import Repository
from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.resources import resources


def _normalize_id(value, allowed_cls, id_field='pk', ischecker=isinstance):
    if ischecker(value, allowed_cls):
        return getattr(value, id_field)
    elif isinstance(value, int):
        return value
    else:
        raise ValueError('Expected int or %r, but got %r instead'
                         % (allowed_cls, value))


#
# APITokenResource
#
def get_api_token_list_url(user, local_site_name=None):
    return resources.api_token.get_list_url(
        local_site_name=local_site_name,
        username=user.username)


def get_api_token_item_url(token, local_site_name=None):
    return resources.api_token.get_item_url(
        local_site_name=local_site_name,
        username=token.user.username,
        api_token_id=token.pk)


#
# ArchivedReviewRequestResource
#
def get_archived_review_request_list_url(username, local_site_name=None):
    return resources.archived_review_request.get_list_url(
        local_site_name=local_site_name,
        username=username)


def get_archived_review_request_item_url(username, object_id,
                                         local_site_name=None):
    return resources.archived_review_request.get_item_url(
        local_site_name=local_site_name,
        username=username,
        review_request_id=object_id)


#
# ChangeResource
#
def get_change_list_url(review_request, local_site_name=None):
    return resources.change.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_change_item_url(changedesc, local_site_name=None):
    return resources.change.get_item_url(
        local_site_name=local_site_name,
        review_request_id=changedesc.review_request.get().display_id,
        change_id=changedesc.pk)


#
# DefaultReviewerResource
#
def get_default_reviewer_list_url(local_site_name=None):
    return resources.default_reviewer.get_list_url(
        local_site_name=local_site_name)


def get_default_reviewer_item_url(default_reviewer_id, local_site_name=None):
    return resources.default_reviewer.get_item_url(
        local_site_name=local_site_name,
        default_reviewer_id=default_reviewer_id)


#
# DiffResource
#
def get_diff_list_url(review_request, local_site_name=None):
    return resources.diff.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_diff_item_url(review_request, diff_revision, local_site_name=None):
    return resources.diff.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diff_revision)


#
# DiffFileAttachmentResource
#
def get_diff_file_attachment_list_url(repository, local_site_name=None):
    return resources.diff_file_attachment.get_list_url(
        local_site_name=local_site_name,
        repository_id=repository.pk)


def get_diff_file_attachment_item_url(attachment, repository,
                                      local_site_name=None):
    return resources.diff_file_attachment.get_item_url(
        local_site_name=local_site_name,
        repository_id=repository.pk,
        file_attachment_id=attachment.pk)


#
# DraftDiffResource
#
def get_draft_diff_list_url(review_request, local_site_name=None):
    return resources.draft_diff.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_draft_diff_item_url(review_request, diff_revision,
                            local_site_name=None):
    return resources.draft_diff.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diff_revision)


#
# DraftFileAttachmentResource
#
def get_draft_file_attachment_list_url(review_request, local_site_name=None):
    return resources.draft_file_attachment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_draft_file_attachment_item_url(review_request, file_attachment_id,
                                       local_site_name=None):
    return resources.draft_file_attachment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        file_attachment_id=file_attachment_id)


#
# DraftFileDiffResource
#
def get_draft_filediff_list_url(diffset, review_request, local_site_name=None):
    return resources.draft_filediff.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diffset.revision)


def get_draft_filediff_item_url(filediff, review_request,
                                local_site_name=None):
    return resources.draft_filediff.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=filediff.diffset.revision,
        filediff_id=filediff.pk)


#
# DraftOriginalFileResource
#
def get_draft_original_file_url(review_request, diffset, filediff,
                                local_site_name=None):
    return resources.draft_original_file.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diffset.revision,
        filediff_id=filediff.pk)


#
# DraftPatchedFileResource
#
def get_draft_patched_file_url(review_request, diffset, filediff,
                               local_site_name=None):
    return resources.draft_patched_file.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diffset.revision,
        filediff_id=filediff.pk)


#
# FileAttachmentResource
#
def get_file_attachment_list_url(review_request, local_site_name=None):
    return resources.file_attachment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_file_attachment_item_url(file_attachment, local_site_name=None):
    return resources.file_attachment.get_item_url(
        local_site_name=local_site_name,
        file_attachment_id=file_attachment.id,
        review_request_id=file_attachment.review_request.get().display_id)


#
# FileAttachmentCommentResource
#
def get_file_attachment_comment_list_url(file_attachment,
                                         local_site_name=None):
    return resources.file_attachment_comment.get_list_url(
        local_site_name=local_site_name,
        file_attachment_id=file_attachment.pk,
        review_request_id=file_attachment.review_request.get().display_id)


def get_file_attachment_comment_item_url(file_attachment, comment_id,
                                         local_site_name=None):
    return resources.file_attachment_comment.get_item_url(
        local_site_name=local_site_name,
        file_attachment_id=file_attachment.pk,
        review_request_id=file_attachment.review_request.get().display_id,
        comment_id=comment_id)


#
# FileDiffResource
#
def get_filediff_list_url(diffset, review_request, local_site_name=None):
    return resources.filediff.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diffset.revision)


def get_filediff_item_url(filediff, review_request, local_site_name=None):
    return resources.filediff.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=filediff.diffset.revision,
        filediff_id=filediff.pk)


#
# FileDiffCommentResource
#
def get_filediff_comment_list_url(filediff, local_site_name=None):
    diffset = filediff.diffset
    review_request = diffset.history.review_request.get()

    return resources.filediff_comment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=filediff.diffset.revision,
        filediff_id=filediff.pk)


def get_filediff_comment_item_url(filediff, comment_id, local_site_name=None):
    diffset = filediff.diffset
    review_request = diffset.history.review_request.get()

    return resources.filediff_comment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=filediff.diffset.revision,
        filediff_id=filediff.pk,
        comment_id=comment_id)


#
# HostingServiceResource
#
def get_hosting_service_list_url(local_site_name=None):
    return resources.hosting_service.get_list_url(
        local_site_name=local_site_name)


def get_hosting_service_item_url(hosting_service_or_id, local_site_name=None):
    hosting_service_id = _normalize_id(hosting_service_or_id,
                                       HostingService,
                                       id_field='id',
                                       ischecker=issubclass)

    return resources.hosting_service.get_item_url(
        local_site_name=local_site_name,
        hosting_service_id=hosting_service_id)


#
# HostingServiceAccountResource
#
def get_hosting_service_account_list_url(local_site_name=None):
    return resources.hosting_service_account.get_list_url(
        local_site_name=local_site_name)


def get_hosting_service_account_item_url(account_or_id, local_site_name=None):
    account_id = _normalize_id(account_or_id, HostingServiceAccount)

    return resources.hosting_service_account.get_item_url(
        local_site_name=local_site_name,
        account_id=account_id)


#
# OriginalFileResource
#
def get_original_file_url(review_request, diffset, filediff,
                          local_site_name=None):
    return resources.original_file.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diffset.revision,
        filediff_id=filediff.pk)


#
# PatchedFileResource
#
def get_patched_file_url(review_request, diffset, filediff,
                         local_site_name=None):
    return resources.patched_file.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diffset.revision,
        filediff_id=filediff.pk)


#
# RemoteRepositoryResource
#
def get_remote_repository_list_url(account, local_site_name=None):
    return resources.remote_repository.get_list_url(
        local_site_name=local_site_name,
        account_id=account.pk)


def get_remote_repository_item_url(remote_repository, local_site_name=None):
    return resources.remote_repository.get_item_url(
        local_site_name=local_site_name,
        account_id=remote_repository.hosting_service_account.pk,
        repository_id=remote_repository.id)


#
# RepositoryResource
#
def get_repository_list_url(local_site_name=None):
    return resources.repository.get_list_url(
        local_site_name=local_site_name)


def get_repository_item_url(repository_or_id, local_site_name=None):
    repository_id = _normalize_id(repository_or_id, Repository)

    return resources.repository.get_item_url(
        local_site_name=local_site_name,
        repository_id=repository_id)


#
# RepositoryBranchesResource
#
def get_repository_branches_url(repository, local_site_name=None):
    return resources.repository_branches.get_list_url(
        local_site_name=local_site_name,
        repository_id=repository.pk)


#
# RepositoryCommitsResource
#
def get_repository_commits_url(repository, local_site_name=None):
    return resources.repository_commits.get_list_url(
        local_site_name=local_site_name,
        repository_id=repository.pk)


#
# RepositoryInfoResource
#
def get_repository_info_url(repository, local_site_name=None):
    return resources.repository_info.get_list_url(
        local_site_name=local_site_name,
        repository_id=repository.pk)


#
# ReviewResource
#
def get_review_list_url(review_request, local_site_name=None):
    return resources.review.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_review_item_url(review_request, review_id, local_site_name=None):
    return resources.review.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        review_id=review_id)


#
# ReviewDiffCommentResource
#
def get_review_diff_comment_list_url(review, local_site_name=None):
    return resources.review_diff_comment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_review_diff_comment_item_url(review, comment_id, local_site_name=None):
    return resources.review_diff_comment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk,
        comment_id=comment_id)


#
# FileAttachmentCommentResource
#
def get_review_file_attachment_comment_list_url(review, local_site_name=None):
    return resources.review_file_attachment_comment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_review_file_attachment_comment_item_url(review, comment_id,
                                                local_site_name=None):
    return resources.review_file_attachment_comment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk,
        comment_id=comment_id)


#
# ReviewGroupResource
#
def get_review_group_list_url(local_site_name=None):
    return resources.review_group.get_list_url(
        local_site_name=local_site_name)


def get_review_group_item_url(group_name, local_site_name=None):
    return resources.review_group.get_item_url(
        local_site_name=local_site_name,
        group_name=group_name)


#
# ReviewGroupUserResource
#
def get_review_group_user_list_url(group_name, local_site_name=None):
    return resources.user.get_list_url(
        local_site_name=local_site_name,
        group_name=group_name)


def get_review_group_user_item_url(group_name, username, local_site_name=None):
    return resources.user.get_item_url(
        local_site_name=local_site_name,
        group_name=group_name,
        username=username)


#
# ReviewReplyResource
#
def get_review_reply_list_url(review, local_site_name=None):
    return resources.review_reply.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_review_reply_item_url(review, reply_id, local_site_name=None):
    return resources.review_reply.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk,
        reply_id=reply_id)


#
# ReviewReplyDiffCommentResource
#
def get_review_reply_diff_comment_list_url(reply, local_site_name=None):
    return resources.review_reply_diff_comment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=reply.review_request.display_id,
        review_id=reply.base_reply_to_id,
        reply_id=reply.pk)


def get_review_reply_diff_comment_item_url(reply, comment_id,
                                           local_site_name=None):
    return resources.review_reply_diff_comment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=reply.review_request.display_id,
        review_id=reply.base_reply_to_id,
        reply_id=reply.pk,
        comment_id=comment_id)


#
# ReviewReplyFileAttachmentCommentResource
#
def get_review_reply_file_attachment_comment_list_url(reply,
                                                      local_site_name=None):
    return resources.review_reply_file_attachment_comment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=reply.review_request.display_id,
        review_id=reply.base_reply_to_id,
        reply_id=reply.pk)


def get_review_reply_file_attachment_comment_item_url(reply, comment_id,
                                                      local_site_name=None):
    return resources.review_reply_file_attachment_comment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=reply.review_request.display_id,
        review_id=reply.base_reply_to_id,
        reply_id=reply.pk,
        comment_id=comment_id)


#
# ReviewReplyScreenshotCommentResource
#
def get_review_reply_screenshot_comment_list_url(reply, local_site_name=None):
    return resources.review_reply_screenshot_comment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=reply.review_request.display_id,
        review_id=reply.base_reply_to_id,
        reply_id=reply.pk)


def get_review_reply_screenshot_comment_item_url(reply, comment_id,
                                                 local_site_name=None):
    return resources.review_reply_screenshot_comment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=reply.review_request.display_id,
        review_id=reply.base_reply_to_id,
        reply_id=reply.pk,
        comment_id=comment_id)


#
# ReviewRequestResource
#
def get_review_request_list_url(local_site_name=None):
    return resources.review_request.get_list_url(
        local_site_name=local_site_name)


def get_review_request_item_url(review_request_id, local_site_name=None):
    return resources.review_request.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request_id)


#
# ReviewRequestDraftResource
#
def get_review_request_draft_url(review_request, local_site_name=None):
    return resources.review_request_draft.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


#
# ReviewScreenshotCommentResource
#
def get_review_screenshot_comment_list_url(review, local_site_name=None):
    return resources.review_screenshot_comment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_review_screenshot_comment_item_url(review, comment_id,
                                           local_site_name=None):
    return resources.review_screenshot_comment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk,
        comment_id=comment_id)


#
# RootResource
#
def get_root_url(local_site_name=None):
    return local_site_reverse('root-resource',
                              local_site_name=local_site_name)


#
# ScreenshotResource
#
def get_screenshot_list_url(review_request_or_id, local_site_name=None):
    review_request_id = _normalize_id(review_request_or_id, ReviewRequest,
                                      id_field='display_id')

    return resources.screenshot.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request_id)


def get_screenshot_item_url(screenshot, local_site_name=None):
    return resources.screenshot.get_item_url(
        local_site_name=local_site_name,
        screenshot_id=screenshot.pk,
        review_request_id=screenshot.review_request.get().display_id)


#
# ScreenshotCommentResource
#
def get_screenshot_comment_list_url(screenshot, local_site_name=None):
    return resources.screenshot_comment.get_list_url(
        local_site_name=local_site_name,
        review_request_id=screenshot.review_request.get().display_id,
        screenshot_id=screenshot.pk)


def get_screenshot_comment_item_url(screenshot, comment_id,
                                    local_site_name=None):
    return resources.screenshot_comment.get_item_url(
        local_site_name=local_site_name,
        review_request_id=screenshot.review_request.get().display_id,
        screenshot_id=screenshot.pk,
        comment_id=comment_id)


#
# ScreenshotDraftResource
#
def get_screenshot_draft_list_url(review_request, local_site_name=None):
    return resources.draft_screenshot.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_screenshot_draft_item_url(review_request, screenshot_id,
                                  local_site_name=None):
    return resources.draft_screenshot.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        screenshot_id=screenshot_id)


#
# ServerInfoResource
#
def get_server_info_url(local_site_name=None):
    return resources.server_info.get_item_url(local_site_name=local_site_name)


#
# SessionResource
#
def get_session_url(local_site_name=None):
    return resources.session.get_list_url(local_site_name=local_site_name)


#
# UserResource
#
def get_user_list_url(local_site_name=None):
    return resources.user.get_list_url(
        local_site_name=local_site_name)


def get_user_item_url(username, local_site_name=None):
    return resources.user.get_item_url(
        local_site_name=local_site_name,
        username=username)


#
# ValidateDiffResource
#
def get_validate_diff_url(local_site_name=None):
    return resources.validate_diff.get_item_url(
        local_site_name=local_site_name)


#
# WatchedReviewGroupResource
#
def get_watched_review_group_list_url(username, local_site_name=None):
    return resources.watched_review_group.get_list_url(
        local_site_name=local_site_name,
        username=username)


def get_watched_review_group_item_url(username, object_id,
                                      local_site_name=None):
    return resources.watched_review_group.get_item_url(
        local_site_name=local_site_name,
        username=username,
        watched_obj_id=object_id)


#
# WatchedReviewRequestResource
#
def get_watched_review_request_list_url(username, local_site_name=None):
    return resources.watched_review_request.get_list_url(
        local_site_name=local_site_name,
        username=username)


def get_watched_review_request_item_url(username, object_id,
                                        local_site_name=None):
    return resources.watched_review_request.get_item_url(
        local_site_name=local_site_name,
        username=username,
        watched_obj_id=object_id)


#
# WebHookResource
#
def get_webhook_list_url(local_site_name=None):
    return resources.webhook.get_list_url(local_site_name=local_site_name)


def get_webhook_item_url(webhook_id, local_site_name=None):
    return resources.webhook.get_item_url(local_site_name=local_site_name,
                                          webhook_id=webhook_id)
