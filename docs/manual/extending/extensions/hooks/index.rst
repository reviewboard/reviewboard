.. _extension-hooks:

===============
Extension Hooks
===============

Extension Hooks are the primary way that your extension will modify behavior or
user interfaces. There are many hooks available that allow changing different
aspects of the tool.


Python Extension Hooks
======================

General Hooks
-------------

:ref:`template-hook`:
  This hook allows you to inject your own content into Review Board's main
  templates at predefined locations.

:ref:`url-hook`
  Defines new URLs in Review Board, which can map to your own custom views.

:ref:`navigation-bar-hook`:
  Adds new links to the very top navigation bar (alongside "My Dashboard",
  "All Review Requests", etc.)

:ref:`signal-hook`:
  Connects to :djangodoc:`signals <topics/signals>`. There are many signals
  built in to Review Board and Django, allowing your extension to run code
  when certain events occur.


Review Request Hooks
--------------------

:ref:`review-request-fields-hook`:
  Creates new fields for a review request.

:ref:`review-request-fieldsets-hook`:
  Creates a new fieldset for a review request, containing multiple fields.


Review Hooks
------------

:ref:`comment-detail-display-hook`:
  Adds additional information to the display of comments on the review
  request page and in e-mails.


Review Workflow Hooks
---------------------

:ref:`review-request-approval-hook`:
  Review Requests have a concept of "approval." This is a flag exposed in the
  API on :ref:`webapi2.0-review-request-resource` that indicates if the change
  has met the necessary requirements to be committed to the codebase.
  This hook allows you to create your own custom policy for how the approved
  flag is set.

:ref:`filediff-acl-hook`:
  This hook allows you to create ACL rules for diffs. This can be used to
  mirror your repository ACLs or organizational rules into access control for
  associated review requests.

:ref:`review-request-condition-choices-hook`:
  Adds new condition choices (for defining rules in integration
  configurations).


File Type Review Hooks
----------------------

:ref:`review-ui-hook`:
  Adds a new Review UI for reviewing file attachments with matching file types.

:ref:`file-attachment-thumbnail-hook`:
  Adds a thumbnail renderer for file attachments with matching file types.


Integration With Third-Party Tools Hooks
----------------------------------------

:ref:`integration-hook`:
  Adds a new integration (for use in :guilabel:`Admin > Integrations`)

:ref:`hosting-service-hook`:
  Adds support for new source code or bug tracker hosting services.

:ref:`scmtool-hook`:
  Adds a new version control system implementation.

:ref:`avatar-service-hook`:
  Adds a new avar service, which can be used to provide profile pictures
  for user accounts.

:ref:`auth-backend-hook`:
  Adds a new authentication backend for logging in to Review Board.


Action Hooks
------------

:ref:`action-hook`:
  Adds new actions for review requests, the diff viewer, and the
  account/support header at the top of the page.

:ref:`hide-action-hook`:
  Hides built-in actions (if you want to disable or replace behavior).


Miscellaneous User Interface Hooks
----------------------------------

:ref:`admin-widget-hook`:
  This hook creates a new widget for use in the main administration UI
  dashboard.

:ref:`account-pages-hook`:
  This hook adds a new sub-page in the :guilabel:`My Account` page.

:ref:`account-page-forms-hook`:
  This hook adds a new form in the :guilabel:`My Account` page.

:ref:`user-details-provider-hook`:
  This hook adds a new user details provider, for providing extra information
  about users.

:ref:`user-infobox-hook`:
  This hook adds new information to user infoboxes (shown when hovering the
  mouse over a username).


Datagrid Hooks
--------------

:ref:`dashboard-columns-hook`:
  This hook adds new columns to the dashboard.

:ref:`datagrid-columns-hook`:
  This hook adds new columns to other datagrids (such as :guilabel:`Users`,
  :guilabel:`Groups`, and :guilabel:`All Review Requests` pages).

:ref:`dashboard-sidebar-items-hook`:
  This hook adds new sections and items to the dashboard sidebar.

:ref:`user-page-sidebar-items-hook`:
  This hook adds sections and items to the user page's sidebar.


API Hooks
---------

:ref:`webapi-capabilities-hook`:
  This hook adds new capability flags no the :ref:`root API resource
  <webapi2.0-root-resource>`. Clients can use this to determine whether
  particular features are available.

:ref:`api-extra-data-access-hook`:
  This hook allows customizing the visibility and mutability of keys in
  ``extra_data`` fields. This allows you to make certain data private or
  read-only.


E-mail Hooks
------------

:ref:`email-hook`:
  Allows modifying recipient lists for outgoing e-mails. This is a generic hook
  which allows handling all notification e-mails.

:ref:`review-request-published-email-hook`:
  Updates information for e-mails about publishing review requests.

:ref:`review-request-closed-email-hook`:
  Updates information for e-mails about closing review requests.

:ref:`review-published-email-hook`:
  Updates information for e-mails about new reviews.

:ref:`review-reply-published-email-hook`:
  Updates information for e-mails about new replies.


.. _js-extensions-hooks:

JavaScript Extension Hooks
==========================

When writing a :ref:`JavaScript extension <js-extensions>`, you can make use
of some special hooks to augment behavior in Review Board's UI. These work
very similar to Python hooks.

:ref:`js-comment-dialog-hook`:
  Adds new fields or content to the comment dialog.

:ref:`js-review-dialog-hook`:
  Adds new fields or content to the top of the review dialog.

:ref:`js-review-dialog-comment-hook`:
  Adds new fields or content to comments within the review dialog.

:ref:`js-file-attachment-thumbnail-container-hook`:
  Adds new content or file actions to file attachment thumbnails.


Deprecated Hooks
================

:py:class:`~reviewboard.extensions.hooks.DiffViewerActionHook`:
  Deprecated hook for adding actions to the diff viewer's review request
  actions bar.

:py:class:`~reviewboard.extensions.hooks.HeaderActionHook`:
  Deprecated hook for adding actions to the top-right of the page.

:py:class:`~reviewboard.extensions.hooks.HeaderDropdownActionHook`:
  Deprecated hook for adding drop-down actions to the top-right of the page.

:py:class:`~reviewboard.extensions.hooks.ReviewRequestActionHook`:
  Deprecated hook for adding actions to the review request actions bar.

:py:class:`~reviewboard.extensions.hooks.ReviewRequestDropdownActionHook`:
  Deprecated hook for adding drop-down actions to the review request actions
  bar.


.. toctree::
   :hidden:

   account-page-forms-hook
   account-pages-hook
   action-hooks
   admin-widget-hook
   api-extra-data-access-hook
   auth-backend-hook
   avatar-service-hook
   comment-detail-display-hook
   dashboard-columns-hook
   dashboard-sidebar-items-hook
   datagrid-columns-hook
   email-hook
   file-attachment-thumbnail-hook
   filediff-acl-hook
   hide-action-hook
   hosting-service-hook
   integration-hook
   navigation-bar-hook
   review-request-approval-hook
   review-request-condition-choices-hook
   review-request-fields-hook
   review-request-fieldsets-hook
   review-ui-hook
   scmtool-hook
   signal-hook
   template-hook
   url-hook
   user-details-provider-hook
   user-infobox-hook
   user-page-sidebar-items-hook
   webapi-capabilities-hook
