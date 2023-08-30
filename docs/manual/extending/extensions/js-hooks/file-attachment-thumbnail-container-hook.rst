.. _js-file-attachment-thumbnail-container-hook:

====================================
FileAttachmentThumbnailContainerHook
====================================

:js:class:`RB.FileAttachmentThumbnailContainerHook` is used to add additional
content on file attachment thumbnail containers or add file actions to file
attachment actions menu. This should not be used to create or modify the
thumbnail image itself, use :py:class:`~reviewboard.extensions.hooks
.FileAttachmentThumbnailHook` for that behavior instead.

The hook is instantiated with a ``viewType`` option that expects a custom
Backbone.js_ view class, which is your custom view for modifying the thumbnail.
The view should inherit from :backbonejs:`View` (or a subclass of this), and
will take the following options:

``thumbnailView``:
    The instance of the :js:class:`RB.FileAttachmentThumbnailView` view, which
    manages the UI of the file attachment thumbnail.

``fileAttachment``:
    The instance of the :js:class:`RB.FileAttachment` model, which handles
    logic, storage, and API access for the file attachment.

It will also be bound to the same element as the thumbnail container, allowing
you to perform queries and modifications to ``this.$el``.

The view's :py:meth:`render` may be called more than once, so if you are
appending any new elements you should clear them first.

Consumers of this hook must take care to code defensively, as some of the
structure of the thumbnail DOM elements may change in future releases.


Example
=======

.. code-block:: javascript

    const MyThumbnailHookView = Backbone.View.extend({
        initialize(options) {
            this.extension = options.extension;
            this.thumbnailView = options.thumbnailView;
            this.fileAttachment = options.fileAttachment;
        },

        render() {
            this.$('.my-file-caption-footer').remove();

            this.$('.file-caption-container').append(
                `<p class="my-file-caption-footer">My footer</p>`);

            /* Add a new action underneath the file download one. */
            this.thumbnailView.addAction(
                'file-download',
                'my-action',
                '<a href="myLink">My action</a>');
        }
    });

    MyProject.Extension = RB.Extension.extend({
        initialize() {
            RB.Extension.prototype.initialize.call(this);

            new RB.FileAttachmentThumbnailContainerHook({
                extension: this,
                viewType: MyThumbnailHookView,
            });
        }
    });

.. _Backbone.js: http://backbonejs.org/
