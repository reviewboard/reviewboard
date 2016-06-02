.. _extension-hooks:

===============
Extension Hooks
===============

Extension hooks are the primary mechanism for customizing Review Board's
appearance and behavior.

Hooks need only be instantiated for Review Board to "notice" them, and are
automatically removed when the extension shuts down.

The following hooks are available for use by extensions.


.. toctree::
   :maxdepth: 1

   auth-backend-hook
   account-pages-hook
   account-page-forms-hook
   action-hook
   admin-widget-hook
   api-extra-data-access-hook
   comment-detail-display-hook
   dashboard-sidebar-items-hook
   dashboard-columns-hook
   datagrid-columns-hook
   email-hook
   file-attachment-thumbnail-hook
   hosting-service-hook
   navigation-bar-hook
   review-request-approval-hook
   review-request-fieldsets-hook
   review-request-fields-hook
   review-ui-hook
   signal-hook
   template-hook
   url-hook
   user-page-sidebar-items-hook
   webapi-capabilities-hook
