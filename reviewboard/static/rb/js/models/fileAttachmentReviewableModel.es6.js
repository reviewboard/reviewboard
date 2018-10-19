/**
 * Provides generic review capabilities for file attachments.
 *
 * Model Attributes:
 *     attachmentRevisionIDs (Array of number):
 *         The revisions of the file attachment.
 *
 *     diffAgainstFileAttachmentID (number):
 *         The ID of the file attachment being diffed against.
 *
 *     diffCaption (string):
 *         The caption of the attachment being diffed against.
 *
 *     diffRevision (number):
 *         The revision of the attachment being diffed against.
 *
 *     diffTypeMismatch (boolean):
 *         Whether the attachments being diffed have different review UI types.
 *
 *     fileAttachmentID (number):
 *         The ID of the file attachment being reviewed.
 *
 *     fileRevision (number):
 *         The revision of the file attachment being reviewed.
 *
 *     filename (string):
 *         The name of the file being reviewed.
 *
 *     numRevision (number):
 *         The total number of revisions for the given attachment.
 *
 * See Also:
 *     :js:class:`RB.AbstractReviewable`:
 *         For attributes defined on the base model.
 */
RB.FileAttachmentReviewable = RB.AbstractReviewable.extend({
    defaults: _.defaults({
        attachmentRevisionIDs: null,
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
