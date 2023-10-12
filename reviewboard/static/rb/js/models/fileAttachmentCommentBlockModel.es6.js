/**
 * Represents the comments on a file attachment.
 *
 * FileAttachmentCommentBlock deals with creating and representing comments
 * that exist on a file attachment. It's a base class that is meant to be
 * subclassed.
 *
 * Model Attributes:
 *     fileAttachmentID (number):
 *         The ID of the file attachment being commented upon.
 *
 *     diffAgainstFileAttachmentID (number):
 *         An optional ID of the file attachment being diffed against.
 *
 *     state (string):
 *         The state of the file attachment.
 *
 * See Also:
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For attributes defined on the base model.
 */
RB.FileAttachmentCommentBlock = RB.AbstractCommentBlock.extend({
    defaults: _.defaults({
        diffAgainstFileAttachmentID: null,
        fileAttachmentID: null,
        state: null,
    }, RB.AbstractCommentBlock.prototype.defaults),

    /**
     * The list of extra fields on this model.
     *
     * These will be stored on the server in the FileAttachmentComment's
     * extra_data field.
     */
    serializedFields: [],

    /**
     * Create a FileAttachmentComment for the given comment ID.
     *
     * The subclass's storeCommentData will be called, allowing additional
     * data to be stored along with the comment.
     *
     * Args:
     *     id (number):
     *         The ID of the comment to instantiate the model for.
     *
     * Returns:
     *     RB.FileAttachmentComment:
     *     The new comment model.
     */
    createComment(id) {
        const comment = this.get('review').createFileAttachmentComment(
            id,
            this.get('fileAttachmentID'),
            this.get('diffAgainstFileAttachmentID'));

        _.extend(comment.get('extraData'),
                 _.pick(this.attributes, this.serializedFields));

        return comment;
    },

    /**
     * Return a warning about commenting on a deleted object.
     *
     * Version Added:
     *     6.0
     *
     * Returns:
     *     string:
     *     A warning to display to the user if they're commenting on a deleted
     *     object. Return null if there's no warning.
     */
    getDeletedWarning() {
        if (this.get('state') === RB.FileAttachmentStates.DELETED) {
            return _`This file is deleted and cannot be commented on.`;
        } else {
            return null;
        }
    },

    /**
     * Return a warning about commenting on a draft object.
     *
     * Returns:
     *     string:
     *     A warning to display to the user if they're commenting on a draft
     *     object. Return null if there's no warning.
     */
    getDraftWarning() {
        const state = this.get('state');

        if (state === RB.FileAttachmentStates.NEW ||
            state === RB.FileAttachmentStates.NEW_REVISION ||
            state === RB.FileAttachmentStates.DRAFT) {
            return _`The file for this comment is still a draft. Replacing or
                     deleting the file will delete this comment.`;
        } else {
            return null;
        }
    },
});
