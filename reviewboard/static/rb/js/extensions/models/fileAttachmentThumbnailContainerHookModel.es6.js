/**
 * Provides extensibility for File Attachment thumbnails.
 *
 * This can be used to display additional UI on file attachment containers
 * and on the file attachment actions menu. This should not be used to create
 * or modify the thumbnail image itself, use :py:class:`~reviewboard
 * .extensions.hooks.FileAttachmentThumbnailHook` for that behavior instead.
 *
 * Users of this hook must provide a Backbone View (not an instance) which
 * will modify the File Attachment thumbnail. The view will have access to
 * the FileAttachmentThumbnailView and its FileAttachment model (through
 * the thumbnailView and fileAttachment options passed to the view).
 *
 * Model Attributes:
 *     viewType (Backbone.View):
 *         The view type (not an instance) which will modify the File
 *         Attachment thumbnail.
 *
 * Version Added:
 *     6.0
 */
RB.FileAttachmentThumbnailContainerHook = RB.ExtensionHook.extend({
    hookPoint: new RB.ExtensionHookPoint(),

    defaults: _.defaults({
        viewType: null,
    }, RB.ExtensionHook.prototype.defaults),

    /**
     * Set up the hook.
     */
    setUpHook() {
        console.assert(this.get('viewType'),
                       'FileAttachmentThumbnailContainerHook instance does ' +
                       'not have a "viewType" attribute set.');
    },
});
