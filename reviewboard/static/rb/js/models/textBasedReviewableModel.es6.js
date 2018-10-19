/**
 * Provides generic review capabilities for text-based file attachments.
 *
 * Model Attributes:
 *     viewMode (string):
 *         The mode of text currently being displayed. This is one of:
 *
 *         ``'source'``:
 *             The raw contents of the file.
 *
 *         ``'rendered'``:
 *             The rendered contents of the file, such as for Markdown, etc.
 *
 *     hasRenderedView (boolean):
 *         Whether or not the text has a rendered view, such as for Markdown,
 *         etc.
 */
RB.TextBasedReviewable = RB.FileAttachmentReviewable.extend({
    defaults: _.defaults({
        viewMode: 'source',
        hasRenderedView: false,
    }, RB.FileAttachmentReviewable.prototype.defaults),

    commentBlockModel: RB.TextCommentBlock,

    defaultCommentBlockFields: [
        'viewMode',
    ].concat(RB.FileAttachmentReviewable.prototype.defaultCommentBlockFields),
});
