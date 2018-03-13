.. _extensions-overview:
.. _writing-extensions:

======================
Extending Review Board
======================

Review Board is a highly-extensible code review product. Like a browser, anyone
can write extensions that improve the product, adding new features,
enhancing existing ones, changing the look and feel, and integrating with
other services. Here are just a few examples of what you can accomplish by
writing an extension:

* Modify the user interface to provide new review request actions, fields, or
  update the content of e-mails
* Collect statistics and generate reports
* Connect Review Board with other systems (Slack, IRC, Asana, etc.)
* Add new API for collecting or computing custom data
* Implement review UIs for previously unsupported types of files

This guide will cover some of the basics of extension writing, and provide a
reference to the Review Board codebase.


Extension Basics
================

To begin, you'll want to become familiar with a few of the basics of extension
writing.

.. toctree::
   :maxdepth: 1

   Extension files/package layout <extensions/file-layout>
   Creating an extension class <extensions/class>
   Configuration <extensions/configuration>
   Providing database models <extensions/models>
   Working with static media files <extensions/static-files>
   Writing JavaScript extensions <extensions/js-extensions>
   Writing extension unit tests <extensions/testing>
   Packaging and distributing extensions <extensions/distribution>


.. tip::

   To get started quickly, you can use :ref:`rbext-create` to create your
   initial page and extension source code. This won't write your whole
   extension for you, of course, but it's a good way of getting the basics in
   place.

   .. versionadded:: 3.0.4


.. _extension-hooks:

Python Extension Hooks
======================

Review Board provides what we call "extension hooks," which are areas that an
extension can hook into in order to modify behavior or UI. There are many
extension hooks available to you.

.. If you add to this list, make sure to also add to
   extensions/hooks/index.rst.

**General Utility Hooks:**
    :ref:`signal-hook`:
        Connects to signals defined by Review Board, Django, or other
        projects.

**General Page Content Hooks:**
    :ref:`navigation-bar-hook`:
        Adds new navigation options to the page alongside "Dashboard," "All
        Review Requests," etc.

    :ref:`template-hook`:
        Adds new content to existing templates.

    :ref:`url-hook`:
        Defines new URLs in Review Board, which can point to your own custom
        views.

    :ref:`avatar-service-hook`:
        Adds a new avatar service, which can be used to provide pictures for
        user accounts.

:ref:`Action Hooks <action-hooks>`:
    A series of hooks used to add new actions for review requests, the diff
    viewer, and the account/support header at the top of the page.

    The following action hooks are available:

    .. To do: Add dedicated doc pages for these.

    :py:class:`~reviewboard.extensions.hooks.DiffViewerActionHook`:
        Adds actions to the diff viewer's review request actions bar.

    :py:class:`~reviewboard.extensions.hooks.HeaderActionHook`:
        Adds actions to the top-right of the page.

    :py:class:`~reviewboard.extensions.hooks.HeaderDropdownActionHook`:
        Adds drop-down actions to the top-right of the page.

    :py:class:`~reviewboard.extensions.hooks.ReviewRequestActionHook`:
        Adds actions to the review request actions bar.

    :py:class:`~reviewboard.extensions.hooks.ReviewRequestDropdownActionHook`:
        Adds drop-down actions to the review request actions bar.

**API Hooks:**
    :ref:`webapi-capabilities-hook`:
        Adds new capability flags to the :ref:`root API resource
        <webapi2.0-root-resource>` that clients of the API can use to
        determine whether particular features or capabilities are active.

    :ref:`api-extra-data-access-hook`:
        Allows for customizing visibility and mutation for keys in
        ``extra_data`` fields, allowing fields to be private or read-only.

**Datagrid Hooks:**
    :ref:`dashboard-columns-hook`:
        Adds new columns to the dashboard, for additional information display.

    :ref:`dashboard-sidebar-items-hook`:
        Add sections and items to the Dashboard sidebar, where the lists of
        groups are displayed.

    :ref:`datagrid-columns-hook`:
        Adds new columns to other datagrids (like the users, groups, and All
        Review Requests pages).

    :ref:`user-page-sidebar-items-hook`:
        Add sections and items to the user page's sidebar, where information
        on the user is normally shown.

**Review-related Hooks:**
    :ref:`comment-detail-display-hook`:
        Adds additional information to the displayed comments on reviews in
        the review request page and in e-mails.

    :ref:`file-attachment-thumbnail-hook`:
        Adds thumbnail renderers for file attachments matching certain
        mimetypes.

    :ref:`review-request-approval-hook`:
        Adds new logic indicating whether a review request can been approved
        for landing in the codebase.

    :ref:`review-request-fields-hook`:
        Adds new fields to the review request.

    :ref:`review-request-fieldsets-hook`:
        Adds new fieldsets to the review request.

    :ref:`review-ui-hook`:
        Adds new review UIs for reviewing file attachments matching certain
        mimetypes.

:ref:`E-mail hooks <email-hook>`:
    A series of hooks that allow for updating recipients lists for outgoing
    e-mails.

    The following e-mail hooks are available:

    :ref:`review-request-published-email-hook`:
        Updates information for e-mails about publishing review requests.

    :ref:`review-request-closed-email-hook`:
        Updates information for e-mails about closing review requests.

    :ref:`review-published-email-hook`:
        Updates information for e-mails about new reviews.

    :ref:`review-reply-published-email-hook`:
        Updates information for e-mails about new replies.

**My Account Page Hooks:**
    :ref:`account-page-forms-hook`:
        Adds new forms in the My Account page.

    :ref:`account-pages-hook`:
        Adds new sub-pages in the My Account page.

**Administrative Hooks:**
    :ref:`admin-widget-hook`:
        Adds new widgets for the administration UI.

    :ref:`auth-backend-hook`:
        Adds a new authentication backend for logging into Review Board.

    :ref:`hosting-service-hook`:
        Adds support for new source code or bug tracker hosting services.

    :ref:`integration-hook`:
        Adds new integration options for services and tools.


.. _js-extensions-hooks:

JavaScript Extension Hooks
==========================

When writing a :ref:`JavaScript extension <js-extensions>`, you can make use
of some special hooks to augment behavior in Review Board's UI. These work
just like Python hooks.

.. If you add to this list, make sure to also add to
   extensions/js-hooks/index.rst.

**Review-related Hooks:**
    :ref:`js-comment-dialog-hook`:
        Adds new fields or content to the comment dialog.

    :ref:`js-review-dialog-comment-hook`:
        Adds new fields or content to comments shown in the review dialog.

    :ref:`js-review-dialog-hook`:
        Adds new fields or content to the top of the review dialog.


Guides to Extending Review Board
================================

We have guides on some of the more common types of extensions you might be
interested in. Note that some of these are still a work-in-progress.

* :ref:`Writing review UIs <extension-review-ui-integration>`
* :ref:`Writing new REST APIs <extension-resources>`
* :ref:`Writing authentication backends <writing-auth-backends>`
* :ref:`Adding review request fields <extension-review-request-fields>`


Code Base Documentation
=======================

When writing extensions, you will be working directly with the same Review
Board classes and methods that we use in the product ourselves.

Please note that not all of these are guaranteed to be API-stable or fully
documented.


Review Board
------------

* :ref:`Review Board Code Base Reference <reviewboard-coderef>`


Djblets
-------

* :ref:`Djblets Development Guides <djblets-guides>`
* :ref:`Djblets Code Base Reference <djblets-coderef>`


.. toctree::
   :hidden:

   extensions/index
   extensions/rbext
   extensions/hooks/index
   extensions/js-hooks/index
   extensions/review-request-fields
   extensions/review-ui
   auth-backends
   legacy-auth-backends
   extensions/webapi
   coderef/index
