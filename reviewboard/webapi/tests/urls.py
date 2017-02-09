from __future__ import unicode_literals

from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.resources import resources


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
# RepositoryResource
#
def get_repository_list_url(local_site_name=None):
    return resources.repository.get_list_url(
        local_site_name=local_site_name)


def get_repository_item_url(repository_or_id, local_site_name=None):
    if isinstance(repository_or_id, int):
        repository_id = repository_or_id
    else:
        repository_id = repository_or_id.pk

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
    return resources.review_group_user.get_list_url(
        local_site_name=local_site_name,
        group_name=group_name)


def get_review_group_user_item_url(group_name, username, local_site_name=None):
    return resources.review_group_user.get_item_url(
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
    if isinstance(review_request_or_id, int):
        review_request_id = review_request_or_id
    else:
        review_request_id = review_request_or_id.display_id

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
# SearchResource
#
def get_search_url(local_site_name=None):
    return resources.search.get_item_url(local_site_name=local_site_name)


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
