from reviewboard.site.urlresolvers import local_site_reverse
from reviewboard.webapi.resources import (
    change_resource,
    default_reviewer_resource,
    diffset_resource,
    draft_file_attachment_resource,
    draft_screenshot_resource,
    file_attachment_resource,
    filediff_comment_resource,
    repository_branches_resource,
    repository_commits_resource,
    repository_info_resource,
    repository_resource,
    review_diff_comment_resource,
    review_file_comment_resource,
    review_group_resource,
    review_reply_resource,
    review_request_draft_resource,
    review_request_resource,
    review_resource,
    review_screenshot_comment_resource,
    screenshot_comment_resource,
    screenshot_resource,
    server_info_resource,
    session_resource,
    user_resource,
    validate_diff_resource,
    watched_review_group_resource,
    watched_review_request_resource)


#
# ChangeResource
#
def get_change_item_url(changedesc, local_site_name=None):
    return change_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=changedesc.review_request.get().display_id,
        change_id=changedesc.pk)


#
# DefaultReviewerResource
#
def get_default_reviewer_list_url(local_site_name=None):
    return default_reviewer_resource.get_list_url(
        local_site_name=local_site_name)


def get_default_reviewer_item_url(default_reviewer_id, local_site_name=None):
    return default_reviewer_resource.get_item_url(
        local_site_name=local_site_name,
        default_reviewer_id=default_reviewer_id)


#
# DiffResource
#
def get_diff_list_url(review_request, local_site_name=None):
    return diffset_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_diff_item_url(review_request, diff_revision, local_site_name=None):
    return diffset_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=diff_revision)


#
# DraftFileAttachmentResource
#
def get_draft_file_attachment_list_url(review_request, local_site_name=None):
    return draft_file_attachment_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_draft_file_attachment_item_url(review_request, file_attachment_id,
                                       local_site_name=None):
    return draft_file_attachment_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        file_attachment_id=file_attachment_id)


#
# FileAttachmentResource
#
def get_file_attachment_list_url(review_request, local_site_name=None):
    return file_attachment_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_file_attachment_item_url(file_attachment, local_site_name=None):
    return file_attachment_resource.get_item_url(
        local_site_name=local_site_name,
        file_attachment_id=file_attachment.id,
        review_request_id=file_attachment.review_request.get().display_id)


#
# FileAttachmentCommentResource
#
def get_file_attachment_comment_list_url(review, local_site_name=None):
    return review_file_comment_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_file_attachment_comment_item_url(review, comment_id,
                                         local_site_name=None):
    return review_file_comment_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk,
        comment_id=comment_id)


#
# FileDiffCommentResource
#
def get_filediff_comment_list_url(filediff, local_site_name=None):
    diffset = filediff.diffset
    review_request = diffset.history.review_request.get()

    return filediff_comment_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        diff_revision=filediff.diffset.revision,
        filediff_id=filediff.pk)


#
# RepositoryResource
#
def get_repository_list_url(local_site_name=None):
    return repository_resource.get_list_url(
        local_site_name=local_site_name)


def get_repository_item_url(repository_or_id, local_site_name=None):
    if isinstance(repository_or_id, int):
        repository_id = repository_or_id
    else:
        repository_id = repository_or_id.pk

    return repository_resource.get_item_url(
        local_site_name=local_site_name,
        repository_id=repository_id)


#
# RepositoryBranchesResource
#
def get_repository_branches_url(repository, local_site_name=None):
    return repository_branches_resource.get_list_url(
        local_site_name=local_site_name,
        repository_id=repository.pk)


#
# RepositoryCommitsResource
#
def get_repository_commits_url(repository, local_site_name=None):
    return repository_commits_resource.get_list_url(
        local_site_name=local_site_name,
        repository_id=repository.pk)


#
# RepositoryInfoResource
#
def get_repository_info_url(repository, local_site_name=None):
    return repository_info_resource.get_list_url(
        local_site_name=local_site_name,
        repository_id=repository.pk)


#
# ReviewResource
#
def get_review_list_url(review_request, local_site_name=None):
    return review_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_review_item_url(review_request, review_id, local_site_name=None):
    return review_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        review_id=review_id)


#
# ReviewDiffCommentResource
#
def get_review_diff_comment_list_url(review, local_site_name=None):
    return review_diff_comment_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_review_diff_comment_item_url(review, comment_id, local_site_name=None):
    return review_diff_comment_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk,
        comment_id=comment_id)


#
# ReviewGroupResource
#
def get_review_group_list_url(local_site_name=None):
    return review_group_resource.get_list_url(
        local_site_name=local_site_name)


def get_review_group_item_url(group_name, local_site_name=None):
    return review_group_resource.get_item_url(
        local_site_name=local_site_name,
        group_name=group_name)


#
# ReviewGroupUserResource
#
def get_review_group_user_list_url(group_name, local_site_name=None):
    return user_resource.get_list_url(
        local_site_name=local_site_name,
        group_name=group_name)


def get_review_group_user_item_url(group_name, username, local_site_name=None):
    return user_resource.get_item_url(
        local_site_name=local_site_name,
        group_name=group_name,
        username=username)


#
# ReviewReplyResource
#
def get_review_reply_list_url(review, local_site_name=None):
    return review_reply_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_review_reply_item_url(review, reply_id, local_site_name=None):
    return review_reply_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk,
        reply_id=reply_id)


#
# ReviewRequestResource
#
def get_review_request_list_url(local_site_name=None):
    return review_request_resource.get_list_url(
        local_site_name=local_site_name)


def get_review_request_item_url(review_request_id, local_site_name=None):
    return review_request_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request_id)


#
# ReviewRequestDraftResource
#
def get_review_request_draft_url(review_request, local_site_name=None):
    return review_request_draft_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


#
# ReviewScreenshotCommentResource
#
def get_review_screenshot_comment_list_url(review, local_site_name=None):
    return review_screenshot_comment_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_review_screenshot_comment_item_url(review, comment_id,
                                           local_site_name=None):
    return review_screenshot_comment_resource.get_item_url(
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

    return screenshot_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request_id)


#
# ScreenshotCommentResource
#
def get_screenshot_comment_list_url(review, local_site_name=None):
    return screenshot_comment_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk)


def get_screenshot_comment_item_url(review, comment_id, local_site_name=None):
    return screenshot_comment_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review.review_request.display_id,
        review_id=review.pk,
        comment_id=comment_id)


#
# ScreenshotDraftResource
#
def get_screenshot_draft_list_url(review_request, local_site_name=None):
    return draft_screenshot_resource.get_list_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id)


def get_screenshot_draft_item_url(review_request, screenshot_id,
                                  local_site_name=None):
    return draft_screenshot_resource.get_item_url(
        local_site_name=local_site_name,
        review_request_id=review_request.display_id,
        screenshot_id=screenshot_id)


#
# ServerInfoResource
#
def get_server_info_url(local_site_name=None):
    return server_info_resource.get_item_url(local_site_name=local_site_name)


#
# SessionResource
#
def get_session_url(local_site_name=None):
    return session_resource.get_list_url(local_site_name=local_site_name)


#
# UserResource
#
def get_user_list_url(local_site_name=None):
    return user_resource.get_list_url(
        local_site_name=local_site_name)


def get_user_item_url(username, local_site_name=None):
    return user_resource.get_item_url(
        local_site_name=local_site_name,
        username=username)


#
# ValidateDiffResource
#
def get_validate_diff_url(local_site_name=None):
    return validate_diff_resource.get_item_url(
        local_site_name=local_site_name)


#
# WatchedReviewGroupResource
#
def get_watched_review_group_list_url(username, local_site_name=None):
    return watched_review_group_resource.get_list_url(
        local_site_name=local_site_name,
        username=username)


def get_watched_review_group_item_url(username, object_id,
                                      local_site_name=None):
    return watched_review_group_resource.get_item_url(
        local_site_name=local_site_name,
        username=username,
        watched_obj_id=object_id)


#
# WatchedReviewRequestResource
#
def get_watched_review_request_list_url(username, local_site_name=None):
    return watched_review_request_resource.get_list_url(
        local_site_name=local_site_name,
        username=username)


def get_watched_review_request_item_url(username, object_id,
                                        local_site_name=None):
    return watched_review_request_resource.get_item_url(
        local_site_name=local_site_name,
        username=username,
        watched_obj_id=object_id)
