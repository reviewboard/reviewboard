.. _extension-review-ui-integration:

Review UI Integration
=====================

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
demonstrate the key anatomical points for integrating ReviewUIs through
extensions.


.. _extension-subclassing-review-ui-hook:

Subclassing ReviewUIHook
------------------------

:file:`extension.py` must use a Review UI Hook to register its list of Review
UIs.  This can be using :py:class:`reviewboard.extensions.hooks.ReviewUIHook`
directly, using a subclass of it. :py:class:`ReviewUIHook` expects a list of
Review UIs as argument in addition to the extension instance.

Example: **XMLReviewUIExtension**::

    class XMLReviewUIExtension(Extension):
        def __init__(self, *args, **kwargs):
            super(XMLReviewUIExtension, self).__init__(*args, **kwargs)
            self.reviewui_hook = ReviewUIHook(self, [XMLReviewUI])


.. _extension-review-ui-class:

ReviewUI Class
--------------

Each Review UI must be defined by its own ReviewUI class that subclasses
:py:class:`reviewboard.reviews.ui.base.FileAttachmentReviewUI`. It must also
define the following class variables:

*
    **supported_mimetypes**: a list of mimetypes of the files that this Review
    UI will be responsible for rendering.

*
    **template_name**: where to find the html template used when rendering this
    Review UI

*
    **object_key**: a unique name to identify this Review UI

Example: **XMLReviewUI**::

    import logging

    from django.utils.encoding import force_unicode
    import pygments

    from reviewboard.reviews.ui.base import FileAttachmentReviewUI


    class XMLReviewUI(FileAttachmentReviewUI):
        """ReviewUI for XML mimetypes"""
        supported_mimetypes = ['application/xml', 'text/xml']
        template_name = 'xml_review_ui_extension/xml.html'
        object_key = 'xml'

The class should also have some function to render the particular mimetype(s)
that it is responsible for. There are no restrictions on the name of the
function or what it returns, but it should be in agreement with logic specified
in its corresponding template.

Example: **render()** in **XMLReviewUI**. This simply uses the pygments API
to convert raw XML into syntax-highlighted HTML::

    def render(self):
        data_string = ""
        f = self.obj.file

        try:
            f.open()
            data_string = f.read()
        except (ValueError, IOError), e:
            logging.error('Failed to read from file %s: %s' % (self.obj.pk, e))

        f.close()

        return pygments.highlight(
            force_unicode(data_string),
            pygments.lexers.XmlLexer(),
            pygments.formatters.HtmlFormatter())


.. _extension_review-ui-template:

ReviewUI Template
-----------------

.. highlight:: html

Here is the template that corresponds to the above Review UI:

:file:`xml_review_ui_extension/templates/xml_review_ui_extension/xml.html`::

    {% extends base_template %}
    {% load i18n %}
    {% load reviewtags %}

    {% block title %}{{xml.filename}}{% if caption %}: {{caption}}
    {% endif %}{% endblock %}

    {% block scripts-post %}
    {{block.super}}

    <script language="javascript"
    src="{{MEDIA_URL}}ext/xml-review-ui-extension/js/XMLReviewableModel.js">
    </script>

    <script language="javascript"
    src="{{MEDIA_URL}}ext/xml-review-ui-extension/js/XMLReviewableView.js">
    </script>

    <script language="javascript">
        $(document).ready(function() {
            var view = new RB.XMLReviewableView({
                model: new RB.XMLReviewable({
                    attachmentID: '{{xml.id}}',
                    caption: '{{caption|escapejs}}',
                    rendered: '{{review_ui.render|escapejs}}'
                })
            });
            view.render();
            $('#xml-review-ui-container').append(view.$el);
        });
    </script>
    {% endblock %}

    {% block review_ui_content %}
    <div id="xml-review-ui-container"></div>
    {% endblock %}


ReviewUI JavaScript
-------------------

.. highlight:: javascript

Here are the corresponding JavaScript used in the above template.

:file:`xml_review_ui_extension/static/js/XMLReviewableModel.js`::

    /*
     * Provides review capabilities for XML files.
     */
    RB.XMLReviewable = RB.FileAttachmentReviewable.extend({
        defaults: _.defaults({
            rendered: ''
        }, RB.FileAttachmentReviewable.prototype.defaults)
    });


:file:`xml_review_ui_extension/static/js/XMLReviewableView.js`::

    /*
     * Displays a review UI for XML files.
     */
    RB.XMLReviewableView = RB.FileAttachmentReviewableView.extend({
        className: 'xml-review-ui',

        /*
         * Renders the view.
         */
        renderContent: function() {
            this.$el.html(this.model.get('rendered'));

            return this;
        }
    });


File Attachment Thumbnails
--------------------------

Most extensions that add Review UIs will also want to render custom thumbnails
for the attachments on the review request page. See
:ref:`extension-file-attachment-thumbnail-hook` for information on how to
implement custom thumbnailers.


.. comment: vim: ft=rst et ts=3
