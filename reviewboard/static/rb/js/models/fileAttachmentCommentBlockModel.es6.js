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
 *     public (boolean):
 *         Whether the diff has been published.
 *
 * See Also:
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For attributes defined on the base model.
 */
RB.FileAttachmentCommentBlock = RB.AbstractCommentBlock.extend({
    defaults: _.defaults({
        fileAttachmentID: null,
        diffAgainstFileAttachmentID: null,
        public: false,
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
     * Return a warning about commenting on a draft object.
     *
     * Returns:
     *     string:
     *     A warning to display to the user if they're commenting on a draft
     *     object. Return null if there's no warning.
     */
    getDraftWarning() {
        if (this.get('public')) {
            return null;
        } else {
            return _`The file for this comment is still a draft. Replacing or deleting the file will delete this comment.`;
        }
    },
});
