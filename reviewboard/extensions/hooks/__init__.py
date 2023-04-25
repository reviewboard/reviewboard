"""Extension hooks for Review Board."""

from djblets.extensions.hooks import (DataGridColumnsHook,
                                      ExtensionHook,
                                      SignalHook,
                                      TemplateHook,
                                      URLHook)
from djblets.privacy.consent.hooks import ConsentRequirementHook

from reviewboard.extensions.hooks.account_page import (AccountPageFormsHook,
                                                       AccountPagesHook)
from reviewboard.extensions.hooks.actions import (
    ActionHook,
    DiffViewerActionHook,
    HeaderActionHook,
    HeaderDropdownActionHook,
    HideActionHook,
    ReviewRequestActionHook,
    ReviewRequestDropdownActionHook)
from reviewboard.extensions.hooks.admin_widget import AdminWidgetHook
from reviewboard.extensions.hooks.api_extra_data_access import \
    APIExtraDataAccessHook
from reviewboard.extensions.hooks.auth_backend import AuthBackendHook
from reviewboard.extensions.hooks.avatar_service import AvatarServiceHook
from reviewboard.extensions.hooks.comment_detail_display import \
    CommentDetailDisplayHook
from reviewboard.extensions.hooks.dashboard import (DashboardColumnsHook,
                                                    DashboardSidebarItemsHook,
                                                    DataGridSidebarItemsHook,
                                                    UserPageSidebarItemsHook)
from reviewboard.extensions.hooks.email import (
    EmailHook,
    ReviewReplyPublishedEmailHook,
    ReviewPublishedEmailHook,
    ReviewRequestClosedEmailHook,
    ReviewRequestPublishedEmailHook)
from reviewboard.extensions.hooks.fields import (ReviewRequestFieldSetsHook,
                                                 ReviewRequestFieldsHook)
from reviewboard.extensions.hooks.file_attachment_thumbnail import \
    FileAttachmentThumbnailHook
from reviewboard.extensions.hooks.filediff_acl import FileDiffACLHook
from reviewboard.extensions.hooks.hosting_service import HostingServiceHook
from reviewboard.extensions.hooks.integration import IntegrationHook
from reviewboard.extensions.hooks.navigation_bar import NavigationBarHook
from reviewboard.extensions.hooks.review_request_approval import \
    ReviewRequestApprovalHook
from reviewboard.extensions.hooks.review_ui import ReviewUIHook
from reviewboard.extensions.hooks.scmtool import SCMToolHook
from reviewboard.extensions.hooks.user_infobox import UserInfoboxHook
from reviewboard.extensions.hooks.webapi_capabilities import \
    WebAPICapabilitiesHook


__all__ = [
    'APIExtraDataAccessHook',
    'AccountPageFormsHook',
    'AccountPagesHook',
    'ActionHook',
    'AdminWidgetHook',
    'AuthBackendHook',
    'AvatarServiceHook',
    'CommentDetailDisplayHook',
    'ConsentRequirementHook',
    'DashboardColumnsHook',
    'DashboardSidebarItemsHook',
    'DataGridColumnsHook',
    'DataGridSidebarItemsHook',
    'DiffViewerActionHook',
    'EmailHook',
    'ExtensionHook',
    'FileAttachmentThumbnailHook',
    'FileDiffACLHook',
    'HeaderActionHook',
    'HeaderDropdownActionHook',
    'HideActionHook',
    'HostingServiceHook',
    'IntegrationHook',
    'NavigationBarHook',
    'ReviewPublishedEmailHook',
    'ReviewReplyPublishedEmailHook',
    'ReviewRequestActionHook',
    'ReviewRequestApprovalHook',
    'ReviewRequestClosedEmailHook',
    'ReviewRequestDropdownActionHook',
    'ReviewRequestFieldSetsHook',
    'ReviewRequestFieldsHook',
    'ReviewRequestPublishedEmailHook',
    'ReviewUIHook',
    'SCMToolHook',
    'SignalHook',
    'TemplateHook',
    'URLHook',
    'UserInfoboxHook',
    'UserPageSidebarItemsHook',
    'WebAPICapabilitiesHook',
]
