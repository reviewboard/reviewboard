/**
 * Provides generic review capabilities for file attachments.
 */
RB.FileAttachmentReviewable = RB.AbstractReviewable.extend({
    defaults: _.defaults({
        attachmentRevisionIDs: null,
        caption: '',
        diffAgainstFileAttachmentID: null,
        diffCaption: '',
        diffRevision: null,
        diffTypeMismatch: false,
        fileAttachmentID: null,
        fileRevision: null,
        filename: '',
        numRevisions: null,
    }, RB.AbstractReviewable.prototype.defaults),

    defaultCommentBlockFields: [
        'fileAttachmentID',
        'diffAgainstFileAttachmentID',
    ],

    /**
     * Load a serialized comment and add comment blocks for it.
     *
     * Args:
     *     serializedCommentBlock (object):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(serializedCommentBlock) {
        const parsedData = this.commentBlockModel.prototype.parse(
            _.pick(serializedCommentBlock[0],
                   this.commentBlockModel.prototype.serializedFields));

        this.createCommentBlock(_.extend(
            {
                fileAttachmentID: this.get('fileAttachmentID'),
                diffAgainstFileAttachmentID:
                    this.get('diffAgainstFileAttachmentID'),
                serializedComments: serializedCommentBlock,
            }, parsedData));
    },
});
