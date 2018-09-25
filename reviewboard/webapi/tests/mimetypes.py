from __future__ import unicode_literals


def _build_mimetype(resource_name, fmt='json'):
    return 'application/vnd.reviewboard.org.%s+%s' % (resource_name, fmt)


api_token_list_mimetype = _build_mimetype('api-tokens')
api_token_item_mimetype = _build_mimetype('api-token')


archived_item_mimetype = _build_mimetype('archived-review-request')


change_list_mimetype = _build_mimetype('review-request-changes')
change_item_mimetype = _build_mimetype('review-request-change')


diff_context_mimetype = _build_mimetype('diff-context')


default_reviewer_list_mimetype = _build_mimetype('default-reviewers')
default_reviewer_item_mimetype = _build_mimetype('default-reviewer')


diff_list_mimetype = _build_mimetype('diffs')
diff_item_mimetype = _build_mimetype('diff')


diffcommit_list_mimetype = _build_mimetype('commits')
diffcommit_item_mimetype = _build_mimetype('commit')


diff_file_attachment_list_mimetype = _build_mimetype('diff-file-attachments')
diff_file_attachment_item_mimetype = _build_mimetype('diff-file-attachment')


draft_diffcommit_list_mimetype = _build_mimetype('draft-commits')
draft_diffcommit_item_mimetype = _build_mimetype('draft-commit')


draft_file_attachment_list_mimetype = _build_mimetype('draft-file-attachments')
draft_file_attachment_item_mimetype = _build_mimetype('draft-file-attachment')


error_mimetype = _build_mimetype('error')


file_attachment_list_mimetype = _build_mimetype('file-attachments')
file_attachment_item_mimetype = _build_mimetype('file-attachment')


file_attachment_comment_list_mimetype = \
    _build_mimetype('file-attachment-comments')
file_attachment_comment_item_mimetype = \
    _build_mimetype('file-attachment-comment')


filediff_list_mimetype = _build_mimetype('files')
filediff_item_mimetype = _build_mimetype('file')


filediff_comment_list_mimetype = _build_mimetype('file-diff-comments')
filediff_comment_item_mimetype = _build_mimetype('file-diff-comment')


general_comment_list_mimetype = _build_mimetype('general-comments')
general_comment_item_mimetype = _build_mimetype('general-comment')


hosting_service_list_mimetype = _build_mimetype('hosting-services')
hosting_service_item_mimetype = _build_mimetype('hosting-service')


hosting_service_account_list_mimetype = \
    _build_mimetype('hosting-service-accounts')
hosting_service_account_item_mimetype = \
    _build_mimetype('hosting-service-account')


oauth_app_list_mimetype = _build_mimetype('oauth-apps')
oauth_app_item_mimetype = _build_mimetype('oauth-app')


oauth_token_list_mimetype = _build_mimetype('oauth-tokens')
oauth_token_item_mimetype = _build_mimetype('oauth-token')


original_file_mimetype = 'text/plain'
patched_file_mimetype = 'text/plain'


remote_repository_list_mimetype = _build_mimetype('remote-repositories')
remote_repository_item_mimetype = _build_mimetype('remote-repository')


repository_list_mimetype = _build_mimetype('repositories')
repository_item_mimetype = _build_mimetype('repository')


repository_branches_item_mimetype = _build_mimetype('repository-branches')


repository_commits_item_mimetype = _build_mimetype('repository-commits')


repository_info_item_mimetype = _build_mimetype('repository-info')


review_list_mimetype = _build_mimetype('reviews')
review_item_mimetype = _build_mimetype('review')


review_diff_comment_list_mimetype = _build_mimetype('review-diff-comments')
review_diff_comment_item_mimetype = _build_mimetype('review-diff-comment')


review_group_list_mimetype = _build_mimetype('review-groups')
review_group_item_mimetype = _build_mimetype('review-group')


review_group_user_list_mimetype = _build_mimetype('review-group-users')
review_group_user_item_mimetype = _build_mimetype('review-group-user')


review_reply_list_mimetype = _build_mimetype('review-replies')
review_reply_item_mimetype = _build_mimetype('review-reply')


review_request_last_update_mimetype = _build_mimetype('last-update')


review_reply_diff_comment_list_mimetype = \
    _build_mimetype('review-reply-diff-comments')
review_reply_diff_comment_item_mimetype = \
    _build_mimetype('review-reply-diff-comment')


review_reply_file_attachment_comment_list_mimetype = \
    _build_mimetype('review-reply-file-attachment-comments')
review_reply_file_attachment_comment_item_mimetype = \
    _build_mimetype('review-reply-file-attachment-comment')


review_reply_general_comment_list_mimetype = \
    _build_mimetype('review-reply-general-comments')
review_reply_general_comment_item_mimetype = \
    _build_mimetype('review-reply-general-comment')


review_reply_screenshot_comment_list_mimetype = \
    _build_mimetype('review-reply-screenshot-comments')
review_reply_screenshot_comment_item_mimetype = \
    _build_mimetype('review-reply-screenshot-comment')


review_request_list_mimetype = _build_mimetype('review-requests')
review_request_item_mimetype = _build_mimetype('review-request')


review_request_draft_item_mimetype = _build_mimetype('review-request-draft')


root_item_mimetype = _build_mimetype('root')


screenshot_list_mimetype = _build_mimetype('screenshots')
screenshot_item_mimetype = _build_mimetype('screenshot')


screenshot_comment_list_mimetype = _build_mimetype('screenshot-comments')
screenshot_comment_item_mimetype = _build_mimetype('screenshot-comment')


screenshot_draft_item_mimetype = _build_mimetype('draft-screenshot')
screenshot_draft_list_mimetype = _build_mimetype('draft-screenshots')


search_mimetype = _build_mimetype('search')


server_info_mimetype = _build_mimetype('server-info')


session_mimetype = _build_mimetype('session')


status_update_list_mimetype = _build_mimetype('status-updates')
status_update_item_mimetype = _build_mimetype('status-update')


user_list_mimetype = _build_mimetype('users')
user_item_mimetype = _build_mimetype('user')


user_file_attachment_list_mimetype = _build_mimetype('user-file-attachments')
user_file_attachment_item_mimetype = _build_mimetype('user-file-attachment')


validate_diff_mimetype = _build_mimetype('diff-validation')


validate_diffcommit_mimetype = _build_mimetype('commit-validation')


watched_review_group_list_mimetype = _build_mimetype('watched-review-groups')
watched_review_group_item_mimetype = _build_mimetype('watched-review-group')


watched_review_request_item_mimetype = \
    _build_mimetype('watched-review-request')
watched_review_request_list_mimetype = \
    _build_mimetype('watched-review-requests')

webhook_list_mimetype = _build_mimetype('webhooks')
webhook_item_mimetype = _build_mimetype('webhook')
