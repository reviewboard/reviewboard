.. _extensions-template-hook:
.. _template-hook:

============
TemplateHook
============

:py:class:`djblets.extensions.hooks.TemplateHook` is one of the most versatile
hooks, allowing you to inject your own HTML into templates at various points.

Template hooks have three parameters:

*
    **name**: The name of the template hook point to inject into.

*
    **template_name**: The filename of the template to render. This should
    refer to template files in your extensions ``templates`` directory.

*
    **apply_to**: An optional list of URL names to limit this hook to. This is
    useful when using a generic template hook point, but when you only want to
    inject onto a specific page. If this is not provided, the template will be
    rendered for all pages with the given hook point name.


Template Hook Names
===================

All Pages
---------

``base-extrahead``
    Inside the ``<head>`` tag for the page. This is generally used for
    ``<meta>`` tags.

``base-css``
    Right after all Review Board CSS has loaded. This is generally used
    for ``<link>`` or ``<style>`` tags.

    If referencing extension-provided files, it's better to use
    :ref:`static bundles <extension-static-files>` instead.

``base-scripts``
    Toward the top of the page, after initial JavaScript files and before
    any page content. This is generally used for ``<script>`` tags. Note
    that scripts loaded here will delay rendering of the page.

    If referencing extension-provided files, it's better to use
    :ref:`static bundles <extension-static-files>` instead. For everything
    else, we recommend creating a :ref:`JavaScript extension
    <js-extensions>`.

``base-scripts-post``
    Toward the end of the page, after all Review Board JavaScript.
    This is generally used for ``<script>`` tags.

    If referencing extension-provided files, it's better to use
    :ref:`static bundles <extension-static-files>` instead. For everything
    else, we recommend creating a :ref:`JavaScript extension
    <js-extensions>`.

``base-before-nav``
    Toward the top of the page before the navigation bar
    (``#navbar-container``) and after the header bar (``#headerbar``).

``base-after-nav``
    Toward the top of the page after the navigation bar (``#navbar-container``).

``base-before-content``
    Right before the page content (at the beginning of ``#content``).

``base-after-content``
    Right after the page content (at the end of ``#content``).


Login Page
----------

``before-login-form``
    Right before the login form. Useful for displaying login instructions.

``after-login-form``
    Right after the login form. Useful for providing contact information
    in case of login issues.


E-mails
-------

``review-email-html-summary``
    Displayed right before the header text for reviews in HTML e-mails,
    and below any "Ship It!" text.

``review-email-text-summary``
    Displayed right before the header text for reviews in plain text e-mails,
    and below any "Ship It!" text.


.. seealso::

   * :ref:`comment-detail-display-hook`
   * :ref:`email-hook`


Registration Page
-----------------

``before-register-form``
    Displayed right before the new account registration form. Useful for
    displaying login instructions.


``after-register-form``
    Displayed right after the new account registration form. Useful for
    providing contact information in case of login issues.


Review Request Pages
--------------------

``before-review-request-summary``
    The very top of the review request box, right before the summary
    information (containing the Summary field, review request ID, and
    created/updated/closed information). Content here will not be aligned with
    the summary information.

``after-review-request-summary``
    The area right below the review request box's summary information. Content
    here will not be aligned with the summary information.

``review-request-summary-pre``
    The area at the top of the element for the review request box's summary
    information. Content here will be properly padding and aligned with the
    summary information.

``review-request-summary-post``
    The area at the bottom of the element for the review request box's summary
    information. Content here will be properly padding and aligned with the
    summary information.

``before-review-request-fields``
    Right after the summary (and the field validation warning, if shown),
    and right before the fields in the review request box.

``after-review-request-fields``
    Right after the fields in the review request box, and before the extra
    panes shown (file attachments, issue summary table, etc.).

``before-review-request-extra-panes``
    Right after the fields in the review request box, and before the extra
    panes shown (file attachments, issue summary table, etc.).

    This is basically equivalent to ``after-review-request-fields``, but is
    preferable if you're explicitly trying to target the area right before
    the panes. This may impact placement or rendering in the future.

``after-review-request-extra-panes``
   Right after any extra panes shown in the review request box, as the last
   content at the bottom of the box.

``review-request-extra-panes-pre``
   The very top of the element containing extra panes in the review request
   box.

``review-request-extra-panes-post``
   The very bottom of the element containing extra panes in the review request
   box.

``change-summary-header-pre``
    Right before the box's header text for "Review Request Changed" entries.

``change-summary-header-post``
    Right after the box's header text for "Review Request Changed" entries,
    before the change description or fields.

``review-summary-header-pre``
    Right before the box's header text for reviews.

``review-summary-header-post``
    Right after the box's header text for reviews, before any comments.


..
    TODO: Include ones for the initial status updates entry. We might want
          to normalize the ID a bit first, since it uses underscores. For now,
          it's undocumented.

Additional template hook points are trivially added. If these are insufficient
for your needs, please get in touch with the Review Board developer community.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import TemplateHook


    class SampleExtension(Extension):
        def initialize(self):
            TemplateHook(self,
                         name='base-after-nav',
                         template_name='myextension/after-nav.html',
                         apply_to=['view-diff', 'view-diff-revision'])

            TemplateHook(self,
                         name='before-register-form',
                         template_name='myextension/registeration-info.html')
