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

+----------------------------+----------------------------------------------+
| Name                       | Location                                     |
+============================+==============================================+
| base-extrahead             | Inside the <head> tag.                       |
+----------------------------+----------------------------------------------+
| base-css                   | Used to add new CSS.                         |
+----------------------------+----------------------------------------------+
| base-scripts               | <script> tags that need to go at the top.    |
+----------------------------+----------------------------------------------+
| base-before-navbar         | At the top of the page before the            |
|                            | navigation bar.                              |
+----------------------------+----------------------------------------------+
| base-after-navbar          | After the navigation bar but before the      |
|                            | content.                                     |
+----------------------------+----------------------------------------------+
| base-before-content        | Before the content.                          |
+----------------------------+----------------------------------------------+
| base-after-content         | At the end of the content.                   |
+----------------------------+----------------------------------------------+
| base-scripts-post          | <script> tags that go at the end of <body>.  |
+----------------------------+----------------------------------------------+


Login Page
----------

+----------------------------+----------------------------------------------+
| Name                       | Location                                     |
+============================+==============================================+
| before-login-form          | Displayed right before the login form.       |
+----------------------------+----------------------------------------------+
| after-login-form           | Displayed right after the login form.        |
+----------------------------+----------------------------------------------+


Notifications
-------------

+----------------------------+----------------------------------------------+
| Name                       | Location                                     |
+============================+==============================================+
| review-email-html-summary  | Displayed right before the review header.    |
+----------------------------+----------------------------------------------+
| review-email-text-summary  | Displayed right before the review header.    |
+----------------------------+----------------------------------------------+


Registration Page
-----------------

+----------------------------+----------------------------------------------+
| Name                       | Location                                     |
+============================+==============================================+
| before-register-form       | Displayed right before the register form.    |
+----------------------------+----------------------------------------------+
| after-register-form        | Displayed right after the register form.     |
+----------------------------+----------------------------------------------+


Review Request Pages
--------------------

+----------------------------+----------------------------------------------+
| Name                       | Location                                     |
+============================+==============================================+
| change-summary-header-pre  | For each change entry, before the header.    |
+----------------------------+----------------------------------------------+
| change-summary-header-post | For each change entry, after the header but  |
|                            | before before any field changes.             |
+----------------------------+----------------------------------------------+
| review-summary-header-pre  | For each review, before the header.          |
+----------------------------+----------------------------------------------+
| review-summary-header-post | For each review, after the header but before |
|                            | before any comments.                         |
+----------------------------+----------------------------------------------+

Additional template hook points are trivially added. If these are insufficient
for your needs, please get in touch with the Review Board developer community.


Example
=======

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import TemplateHook


    class SampleExtension(Extension):
        def initialize(self):
            TemplateHook(self, 'base-css', 'diff-extension-css.html',
                         apply_to=['view_diff', 'view_diff_revision'])
            TemplateHook(self, 'base-scripts-post', 'diff-extension-js.html',
                         apply_to=['view_diff', 'view_diff_revision'])
