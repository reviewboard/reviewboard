"""Root resource for the Review Board API."""

from djblets.util.decorators import augment_method_from
from djblets.webapi.resources.root import RootResource as DjbletsRootResource

from reviewboard.webapi.server_info import get_server_info
from reviewboard.webapi.decorators import (webapi_check_login_required,
                                           webapi_check_local_site)
from reviewboard.webapi.resources import WebAPIResource, resources


class RootResource(WebAPIResource, DjbletsRootResource):
    """The root of the Review Board API resource tree.

    This should be used as a starting point for any clients that need to access
    any resources in the API. By browsing through the resource tree instead of
    hard-coding paths, your client can remain compatible with any changes in
    the resource URI scheme.

    This also contains information on the server and the capabilities of
    the API. This information was formerly provided only by the Server Info
    resource, but has been moved here as a convenience to clients.


    .. rubric:: URI Templates

    The following URI templates (found in the ``uri_templates`` key) can be
    used to help quickly reach the right API resource.

    .. note::

       This list may have changed between versions of Review Board, with some
       items added and some pointing to corrected URLs. In particular, due to
       a bug on some Python versions, there were differences in Review Board
       4.0.x and 5.0/5.0.1.

       Please check the specific URI templates for your version of Review Board
       if you are having any trouble.

    .. list-table::
       :header-rows: 1

       * - URI template key
         - Resource
         - Version Added

       * - ``all_diff_comments``
         - :ref:`webapi2.0-root-diff-comment-list-resource`
         - 5.0.2

       * - ``all_file_attachment_comments``
         - :ref:`webapi2.0-root-file-attachment-comment-list-resource`
         - 5.0.2

       * - ``all_general_comments``
         - :ref:`webapi2.0-root-general-comment-list-resource`
         - 5.0.1

       * - ``all_reviews``
         - :ref:`webapi2.0-root-review-list-resource`
         - 5.0.1

       * - ``api_token``
         - :ref:`webapi2.0-api-token-resource`
         -

       * - ``api_tokens``
         - :ref:`webapi2.0-api-token-list-resource`
         -

       * - ``archived_review_request``
         - :ref:`webapi2.0-archived-review-request-resource`
         -

       * - ``archived_review_requests``
         - :ref:`webapi2.0-archived-review-request-list-resource`
         -

       * - ``commit_validation``
         - :ref:`webapi2.0-commit-validation-resource`
         -

       * - ``default_reviewer``
         - :ref:`webapi2.0-default-reviewer-resource`
         -

       * - ``default_reviewers``
         - :ref:`webapi2.0-default-reviewer-list-resource`
         -

       * - ``diff``
         - :ref:`webapi2.0-diff-resource`
         -

       * - ``diffs``
         - :ref:`webapi2.0-diff-list-resource`
         -

       * - ``diff_commit``
         - :ref:`webapi2.0-diff-commit-resource`
         - 5.0.2

       * - ``diff_commits``
         - :ref:`webapi2.0-diff-commit-list-resource`
         - 5.0.2

       * - ``diff_context``
         - :ref:`webapi2.0-diff-context-resource`
         -

       * - ``diff_file_attachment``
         - :ref:`webapi2.0-diff-file-attachment-resource`
         -

       * - ``diff_file_attachments``
         - :ref:`webapi2.0-diff-file-attachment-list-resource`
         -

       * - ``diff_validation``
         - :ref:`webapi2.0-validate-diff-resource`
         -

       * - ``extension``
         - :ref:`webapi2.0-extension-resource`
         -

       * - ``extensions``
         - :ref:`webapi2.0-extension-list-resource`
         -

       * - ``file_diff``
         - :ref:`webapi2.0-file-diff-resource`
         - 5.0.2

       * - ``file_diffs``
         - :ref:`webapi2.0-file-diff-list-resource`
         - 5.0.2

       * - ``file_diff_comments``
         - :ref:`webapi2.0-file-diff-comment-list-resource`
         -

       * - ``file_diff_original``
         - :ref:`webapi2.0-original-file-resource`
         - 5.0.2

       * - ``file_diff_patched``
         - :ref:`webapi2.0-patched-file-resource`
         - 5.0.2

       * - ``group``
         - :ref:`webapi2.0-review-group-resource`
         -

       * - ``groups``
         - :ref:`webapi2.0-review-group-list-resource`
         -

       * - ``hosting_service``
         - :ref:`webapi2.0-hosting-service-resource`
         -

       * - ``hosting_services``
         - :ref:`webapi2.0-hosting-service-list-resource`
         -

       * - ``hosting_service_account``
         - :ref:`webapi2.0-hosting-service-account-resource`
         -

       * - ``hosting_service_accounts``
         - :ref:`webapi2.0-hosting-service-account-list-resource`
         -

       * - ``info``
         - :ref:`webapi2.0-server-info-resource`
         -

       * - ``muted_review_request``
         - :ref:`webapi2.0-muted-review-request-resource`
         -

       * - ``muted_review_requests``
         - :ref:`webapi2.0-muted-review-request-list-resource`
         -

       * - ``oauth_app``
         - :ref:`webapi2.0-oauth-application-resource`
         -

       * - ``oauth_apps``
         - :ref:`webapi2.0-oauth-application-list-resource`
         -

       * - ``oauth_token``
         - :ref:`webapi2.0-oauth-token-resource`
         -

       * - ``oauth_tokens``
         - :ref:`webapi2.0-oauth-token-list-resource`
         -

       * - ``remote_repository``
         - :ref:`webapi2.0-remote-repository-resource`
         -

       * - ``remote_repositories``
         - :ref:`webapi2.0-remote-repository-list-resource`
         -

       * - ``repository``
         - :ref:`webapi2.0-repository-resource`
         -

       * - ``repositories``
         - :ref:`webapi2.0-repository-list-resource`
         -

       * - ``repository_branches``
         - :ref:`webapi2.0-repository-branches-resource`
         - 5.0.2

       * - ``repository_commits``
         - :ref:`webapi2.0-repository-commits-resource`
         - 5.0.2

       * - ``repository_group``
         - :ref:`webapi2.0-repository-group-resource`
         - 5.0.2

       * - ``repository_groups``
         - :ref:`webapi2.0-repository-group-list-resource`
         - 5.0.2

       * - ``repository_info``
         - :ref:`webapi2.0-repository-info-resource`
         - 5.0.2

       * - ``repository_user``
         - :ref:`webapi2.0-repository-user-resource`
         - 5.0.2

       * - ``repository_users``
         - :ref:`webapi2.0-repository-user-list-resource`
         - 5.0.2

       * - ``review``
         - :ref:`webapi2.0-review-resource`
         -

       * - ``reviews``
         - :ref:`webapi2.0-review-list-resource`
         -

       * - ``review_diff_comment``
         - :ref:`webapi2.0-review-diff-comment-resource`
         - 5.0.2

       * - ``review_diff_comments``
         - :ref:`webapi2.0-review-diff-comment-list-resource`
         - 5.0.2

       * - ``review_draft``
         - :ref:`webapi2.0-review-draft-resource`
         -

       * - ``review_general_comment``
         - :ref:`webapi2.0-review-general-comment-resource`
         - 5.0.2

       * - ``review_general_comments``
         - :ref:`webapi2.0-review-general-comment-list-resource`
         - 5.0.2

       * - ``review_group_user``
         - :ref:`webapi2.0-review-group-user-resource`
         -

       * - ``review_group_users``
         - :ref:`webapi2.0-review-group-user-list-resource`
         -

       * - ``review_reply``
         - :ref:`webapi2.0-review-reply-resource`
         - 5.0.2

       * - ``review_replies``
         - :ref:`webapi2.0-review-reply-list-resource`
         - 5.0.2

       * - ``review_reply_draft``
         - :ref:`webapi2.0-review-reply-draft-resource`
         - 5.0.2

       * - ``review_reply_diff_comment``
         - :ref:`webapi2.0-review-reply-diff-comment-resource`
         - 5.0.2

       * - ``review_reply_diff_comments``
         - :ref:`webapi2.0-review-reply-diff-comment-list-resource`
         - 5.0.2

       * - ``review_reply_file_attachment_comment``
         - :ref:`webapi2.0-review-reply-file-attachment-comment-resource`
         - 5.0.2

       * - ``review_reply_file_attachment_comments``
         - :ref:`webapi2.0-review-reply-file-attachment-comment-list-resource`
         - 5.0.2

       * - ``review_reply_general_comment``
         - :ref:`webapi2.0-review-reply-general-comment-resource`
         - 5.0.2

       * - ``review_reply_general_comments``
         - :ref:`webapi2.0-review-reply-general-comment-list-resource`
         - 5.0.2

       * - ``review_reply_screenshot_comment``
         - :ref:`webapi2.0-review-reply-screenshot-comment-resource`
         - 5.0.1

       * - ``review_reply_screenshot_comments``
         - :ref:`webapi2.0-review-reply-screenshot-comment-list-resource`
         - 5.0.1

       * - ``review_request``
         - :ref:`webapi2.0-review-request-resource`
         -

       * - ``review_requests``
         - :ref:`webapi2.0-review-request-list-resource`
         -

       * - ``review_request_change``
         - :ref:`webapi2.0-change-resource`
         - 5.0.2

       * - ``review_request_changes``
         - :ref:`webapi2.0-change-list-resource`
         - 5.0.2

       * - ``review_request_draft``
         - :ref:`webapi2.0-review-request-draft-resource`
         - 5.0.2

       * - ``review_request_file_attachment``
         - :ref:`webapi2.0-file-attachment-resource`
         - 5.0.2

       * - ``review_request_file_attachments``
         - :ref:`webapi2.0-file-attachment-list-resource`
         - 5.0.2

       * - ``review_request_file_attachment_comments``
         - :ref:`webapi2.0-file-attachment-comment-list-resource`
         - 5.0.2

       * - ``review_request_last_update``
         - :ref:`webapi2.0-review-request-last-update-resource`
         - 5.0.2

       * - ``review_request_status_update``
         - :ref:`webapi2.0-status-update-resource`
         - 5.0.2

       * - ``review_request_status_updates``
         - :ref:`webapi2.0-status-update-list-resource`
         - 5.0.2

       * - ``root``
         - :ref:`webapi2.0-root-resource`
         -

       * - ``screenshot``
         - :ref:`webapi2.0-screenshot-resource`
         -

       * - ``screenshots``
         - :ref:`webapi2.0-screenshot-list-resource`
         -

       * - ``screenshot_comment``
         - :ref:`webapi2.0-review-screenshot-comment-resource`
         -

       * - ``screenshot_comments``
         - :ref:`webapi2.0-screenshot-comment-list-resource`
         -

       * - ``search``
         - :ref:`webapi2.0-search-resource`
         -

       * - ``session``
         - :ref:`webapi2.0-session-resource`
         -

       * - ``user``
         - :ref:`webapi2.0-user-resource`
         -

       * - ``users``
         - :ref:`webapi2.0-user-list-resource`
         -

       * - ``user_file_attachment``
         - :ref:`webapi2.0-user-file-attachment-resource`
         -

       * - ``user_file_attachments``
         - :ref:`webapi2.0-user-file-attachment-list-resource`
         -

       * - ``validation``
         - :ref:`webapi2.0-validation-resource`
         -

       * - ``watched``
         - :ref:`webapi2.0-watched-resource`
         -

       * - ``watched_review_group``
         - :ref:`webapi2.0-watched-review-group-resource`
         -

       * - ``watched_review_groups``
         - :ref:`webapi2.0-watched-review-group-list-resource`
         -

       * - ``watched_review_request``
         - :ref:`webapi2.0-watched-review-request-resource`
         -

       * - ``watched_review_requests``
         - :ref:`webapi2.0-watched-review-request-list-resource`
         -

       * - ``webhook``
         - :ref:`webapi2.0-web-hook-resource`
         -

       * - ``webhooks``
         - :ref:`webapi2.0-web-hook-list-resource`
         -

    The following URI templates are considered deprecated, and may be
    removed in a future version.

    .. list-table::
       :header-rows: 1

       * - URI template key
         - Replacement
         - Resource
         - Deprecated In

       * - ``branches``
         - ``repository_branches``
         - :ref:`webapi2.0-repository-branches-resource`
         - 5.0.2

       * - ``change``
         - ``review_request_change``
         - :ref:`webapi2.0-change-resource`
         - 5.0.2

       * - ``changes``
         - ``review_request_changes``
         - :ref:`webapi2.0-change-list-resource`
         - 5.0.2

       * - ``commit``
         - ``diff_commit``
         - :ref:`webapi2.0-diff-commit-resource`
         - 5.0.2

       * - ``commits``
         - ``repository_commits``
         - :ref:`webapi2.0-repository-commits-resource`
         - 5.0.2

       * - ``diff_comment``
         - ``review_reply_diff_comment``
         - :ref:`webapi2.0-review-reply-diff-comment-resource`
         - 5.0.2

       * - ``diff_comments``
         - ``review_reply_diff_comments``
         - :ref:`webapi2.0-review-reply-diff-comment-list-resource`
         - 5.0.2

       * - ``draft``
         - ``review_request_draft``
         - :ref:`webapi2.0-review-request-draft-resource`
         - 5.0.2

       * - ``file``
         - ``file_diff``
         - :ref:`webapi2.0-file-diff-resource`
         - 5.0.2

       * - ``files``
         - ``file_diffs``
         - :ref:`webapi2.0-file-diff-list-resource`
         - 5.0.2

       * - ``file_attachment``
         - ``review_request_file_attachment``
         - :ref:`webapi2.0-file-attachment-resource`
         - 5.0.2

       * - ``file_attachments``
         - ``review_request_file_attachments``
         - :ref:`webapi2.0-file-attachment-list-resource`
         - 5.0.2

       * - ``general_comment``
         - ``review_general_comment``
         - :ref:`webapi2.0-review-general-comment-resource`
         - 5.0.2

       * - ``general_comments``
         - ``review_general_comments``
         - :ref:`webapi2.0-review-general-comment-list-resource`
         - 5.0.2

       * - ``last_update``
         - ``review_request_last_update``
         - :ref:`webapi2.0-review-request-last-update-resource`
         - 5.0.2

       * - ``original_file``
         - ``file_diff_original_file``
         - :ref:`webapi2.0-original-file-resource`
         - 5.0.2

       * - ``patched_file``
         - ``file_diff_patched_file``
         - :ref:`webapi2.0-patched-file-resource`
         - 5.0.2

       * - ``reply``
         - ``review_reply``
         - :ref:`webapi2.0-review-reply-resource`
         - 5.0.2

       * - ``replies``
         - ``review_replies``
         - :ref:`webapi2.0-review-reply-list-resource`
         - 5.0.2

       * - ``reply_draft``
         - ``review_reply_draft``
         - :ref:`webapi2.0-review-reply-draft-resource`
         - 5.0.2

       * - ``status_update``
         - ``review_request_status_update``
         - :ref:`webapi2.0-status-update-resource`
         - 5.0.2

       * - ``status_updates``
         - ``review_request_status_update``
         - :ref:`webapi2.0-status-update-list-resource`
         - 5.0.2
    """

    mimetype_vendor = 'reviewboard.org'

    def __init__(self, *args, **kwargs):
        super(RootResource, self).__init__([
            resources.default_reviewer,
            resources.extension,
            resources.hosting_service,
            resources.hosting_service_account,
            resources.oauth_app,
            resources.oauth_token,
            resources.repository,
            resources.review_group,
            resources.review_request,
            resources.root_diff_comment,
            resources.root_file_attachment_comment,
            resources.root_general_comment,
            resources.root_review,
            resources.search,
            resources.server_info,
            resources.session,
            resources.user,
            resources.validation,
            resources.webhook,
        ], *args, **kwargs)

        # Manually include these resources to maintain compatibility with
        # our Python 2.7 API behavior. This is a bandaid for a larger
        # issue that stems from resources that share the same name but
        # have different URI templates.
        self.register_uri_template(
            name='branches',
            relative_path='repositories/{repository_id}/branches/',
            relative_resource=self)
        self.register_uri_template(
            name='change',
            relative_path=(
                'review-requests/{review_request_id}/changes/{change_id}/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='changes',
            relative_path='review-requests/{review_request_id}/changes/',
            relative_resource=self)
        self.register_uri_template(
            name='commit',
            relative_path=(
                'review-requests/{review_request_id}/diffs/'
                '{diff_revision}/commits/{commit_id}/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='commits',
            relative_path='repositories/{repository_id}/commits/',
            relative_resource=self)
        self.register_uri_template(
            name='draft',
            relative_path='review-requests/{review_request_id}/draft/',
            relative_resource=self)
        self.register_uri_template(
            name='file',
            relative_path=(
                'review-requests/{review_request_id}/diffs/'
                '{diff_revision}/files/{filediff_id}/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='files',
            relative_path=(
                'review-requests/{review_request_id}/diffs/'
                '{diff_revision}/files/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='diff_comment',
            relative_path=(
                'review-requests/{review_request_id}/reviews/'
                '{review_id}/replies/{reply_id}/diff-comments/'
                '{comment_id}/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='diff_comments',
            relative_path=(
                'review-requests/{review_request_id}/reviews/'
                '{review_id}/replies/{reply_id}/diff-comments/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='file_attachment',
            relative_path=(
                'review-requests/{review_request_id}/file-attachments/'
                '{file_attachment_id}/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='file_attachments',
            relative_path=(
                'review-requests/{review_request_id}/file-attachments/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='general_comments',
            relative_path=(
                'review-requests/{review_request_id}/reviews/'
                '{review_id}/general-comments/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='general_comment',
            relative_path=(
                'review-requests/{review_request_id}/reviews/'
                '{review_id}/general-comments/{comment_id}/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='last_update',
            relative_path='review-requests/{review_request_id}/last-update/',
            relative_resource=self)
        self.register_uri_template(
            name='original_file',
            relative_path=(
                'review-requests/{review_request_id}/diffs/{diff_revision}/'
                'files/{filediff_id}/original-file/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='patched_file',
            relative_path=(
                'review-requests/{review_request_id}/diffs/{diff_revision}/'
                'files/{filediff_id}/patched-file/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='reply',
            relative_path=(
                'review-requests/{review_request_id}/reviews/{review_id}/'
                'replies/{reply_id}/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='replies',
            relative_path=(
                'review-requests/{review_request_id}/reviews/{review_id}/'
                'replies/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='reply_draft',
            relative_path=(
                'review-requests/{review_request_id}/reviews/{review_id}/'
                'replies/draft/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='search',
            relative_path='search/{username}/',
            relative_resource=self)
        self.register_uri_template(
            name='status_update',
            relative_path=(
                'review-requests/{review_request_id}/status-updates/'
                '{status_update_id}/'
            ),
            relative_resource=self)
        self.register_uri_template(
            name='status_updates',
            relative_path=(
                'review-requests/{review_request_id}/status-updates/'
            ),
            relative_resource=self)

    @webapi_check_login_required
    @webapi_check_local_site
    @augment_method_from(DjbletsRootResource)
    def get(self, request, *args, **kwargs):
        """Retrieves the list of top-level resources and templates."""
        pass

    def serialize_root(self, request, *args, **kwargs):
        root = super(RootResource, self).serialize_root(request, *args,
                                                        **kwargs)
        root.update(get_server_info(request))

        return root


root_resource = RootResource()
