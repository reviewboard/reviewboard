.. _extension-review-ui-integration:

==========================================
Adding UIs for New File Types (Review UIs)
==========================================

Review UIs are used in reviewing file attachments of particular mimetypes. For
example, an Image Review UI is used to render image files and allow comments to
be attached to specific areas of an image. Similarly, a Markdown Review UI
renders the raw text from a .md file into a corresponding HTML.

Extensions can integrate custom Review UIs into Review Board by defining
a hook that subclasses ReviewUIHook. Each extension may define and register
zero or more Review UIs. When the extension is enabled through the admin page,
the hook registers its list of Review UIs. Likewise, the hook unregisters these
Review UIs when the extension is disabled.

We use a simple XMLReviewUI that performs syntax highlighting as an example to
demonstrate the key anatomical points for integrating Review UIs through
extensions.


.. _extension-subclassing-review-ui-hook:

ReviewUIHook
============

:file:`extension.py` must use a
:py:class:`~reviewboard.extensions.hooks.ReviewUIHook` to register its list of
Review UIs. :py:class:`~reviewboard.extensions.hooks.ReviewUIHook` expects a
list of Review UIs as argument in addition to the extension instance.

Since you will be writing custom JavaScript and, likely, custom CSS, you will
also need to define some :ref:`static media bundles <extension-static-files>`
to load. There's no need to set ``apply_to`` for these. Instead you'll set
:py:attr:`~reviewboard.reviews.ui.base.ReviewUI.js_bundle_names` and
:py:attr:`~reviewboard.reviews.ui.base.ReviewUI.css_bundle_names` which will
automatically load the bundles whenever the Review UI is rendered onto a page.

Example: **XMLReviewUIExtension**:

.. code-block:: python

    from reviewboard.extensions.base import Extension
    from reviewboard.extensions.hooks import ReviewUIHook


    class XMLReviewUIExtension(Extension):
        css_bundles = {
            'xmlreviewable': {
                'source_filenames': ['css/xmlreviewable.less'],
            },
        }

        js_bundles = {
            'xmlreviewable': {
                'source_filenames': [
                    'js/XMLReviewableModel.js',
                    'js/XMLReviewableView.js',
                ],
            },
        }

        def initialize(self):
            ReviewUIHook(self, [XMLReviewUI])


.. _extension-review-ui-class:

ReviewUI Class
==============

Each Review UI must be defined by its own ReviewUI class that subclasses
:py:class:`reviewboard.reviews.ui.base.ReviewUI`. Review UIs that support
:py:class:`file attachments <reviewboard.attachments.models.FileAttachment>`
should subclass :py:class:`reviewboard.reviews.ui.base.FileAttachmentReviewUI`
instead.

It must also define the following class variables and properties:

*
    **name**: The name for the review UI.

*
    **supported_mimetypes**: a list of mimetypes of the files that this Review
    UI will be responsible for rendering.

*
    **js_model_class**: The JavaScript model name that will store information
    for the view.

*
    **js_model_view**: The JavaScript view name that will provide the review
    experience for the file.

*
    **css_bundle_names**: A list of CSS bundles defined by your extension
    that the page will include.

*
    **js_bundle_names**: A list of JavaScript bundles defined by your
    extension that the page will include.

It can also define the following optional class variables:

*
    **allow_inline**: A flag indicating whether the Review UI can be rendered
    inline in diffs and other places. If set, the Review UI will be able to
    be displayed within the diff viewer (and potentially other locations).

*
    **load_static_media_inline**: A flag indicating whether to load the
    Review UI's static media when rendered inline.

    If the extension managing the Review UI already loads its static media
    in the diff viewer page or any other page where a Review UI might be
    rendered, then this should be set to ``False`` to prevent duplicate
    loading. This is useful for ensuring that state set in static media
    gets shared among the extension instance and any review UIs on the page
    instead of being overwritten.

*
    **supports_diffing**: A flag indicating whether the Review UI supports
    diffing two objects.


Example: **XMLReviewUI**:

.. code-block:: python

    import logging

    from django.utils.encoding import force_unicode
    from django.utils.functional import cached_property
    import pygments

    from reviewboard.reviews.ui.base import ReviewUI


    class XMLReviewUI(ReviewUI):
        """ReviewUI for XML mimetypes"""
        name = 'XML'
        supported_mimetypes = ['application/xml', 'text/xml']
        supports_file_attachments = True

        js_model_class = 'MyVendor.XMLReviewable'
        js_view_class = 'MyVendor.XMLReviewableView'

        def __init__(self, review_request, obj):
            super().__init__(review_request, obj)

            from xmlreview.reviewui import XMLReviewUIExtension
            self.extension = XMLReviewUIExtension.instance

        @cached_property
        def js_bundle_names(self):
            return [
                self.extension.get_bundle_id('xmlreviewable'),
            ]

        @cached_property
        def css_bundle_names(self):
            return [
                self.extension.get_bundle_id('xmlreviewable'),
            ]


Generally, you will also want to provide data for the model, such as the
contents of the file. You will do this in :py:meth:`get_js_model_data`.
For example:

.. code-block:: python

    def get_js_model_data(self):
        data = super().get_js_model_data()

        data_string = ""

        with self.obj.file as f:
           try:
               f.open()
               data_string = f.read()
           except (ValueError, IOError) as e:
               logging.error('Failed to read from file %s: %s', self.obj.pk, e)

        data['xmlContent'] = pygments.highlight(
            force_unicode(data_string),
            pygments.lexers.XmlLexer(),
            pygments.formatters.HtmlFormatter())

        return data

You may also provide :py:meth:`get_js_view_data` to pass options to the
view.

There are a number of functions you may want to override, all documented in
:py:class:`reviewboard.reviews.ui.base.ReviewUI`.


ReviewUI JavaScript
===================

Here are the corresponding JavaScript used in the above extension.

:file:`xml_review_ui_extension/static/js/XMLReviewableModel.js`:

.. code-block:: javascript

    /*
     * Provides review capabilities for XML files.
     */
    MyVendor.XMLReviewable = RB.FileAttachmentReviewable.extend({
        defaults: _.defaults({
            xmlContent: '',
        }, RB.FileAttachmentReviewable.prototype.defaults)
    });


:file:`xml_review_ui_extension/static/js/XMLReviewableView.js`:

.. code-block:: javascript

    /*
     * Displays a review UI for XML files.
     */
    MyVendor.XMLReviewableView = RB.FileAttachmentReviewableView.extend({
        className: 'xml-review-ui',

        /*
         * Renders the view.
         */
        renderContent() {
            this.$el.html(this.model.get('xmlContent'));

            return this;
        },
    });


File Attachment Thumbnails
==========================

Most extensions that add Review UIs will also want to render custom thumbnails
for the attachments on the review request page. See
:ref:`extension-file-attachment-thumbnail-hook` for information on how to
implement custom thumbnailers.
