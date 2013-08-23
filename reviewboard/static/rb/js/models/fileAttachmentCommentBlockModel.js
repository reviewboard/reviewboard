/*
 * Represents the comments on a file attachment.
 *
 * FileAttachmentCommentBlock deals with creating and representing comments
 * that exist on a file attachment. It's a base class that is meant to be
 * subclassed.
 */
RB.FileAttachmentCommentBlock = RB.AbstractCommentBlock.extend({
    defaults: _.defaults({
        fileAttachmentID: null,
        diffAgainstFileAttachmentID: null
    }, RB.AbstractCommentBlock.prototype.defaults),

    /*
     * The list of fields on this model that will be stored on the server
     * in the FileAttachmentComment's extraData.
     */
    serializedFields: [],

    /*
     * Creates a FileAttachmentComment for the given comment ID.
     *
     * The subclass's storeCommentData will be called, allowing additional
     * data to be stored along with the comment.
     */
    createComment: function(id) {
        var comment = this.get('review').createFileAttachmentComment(
                id,
                this.get('fileAttachmentID'),
                this.get('diffAgainstFileAttachmentID'));

        _.extend(comment.get('extraData'),
                 _.pick(this.attributes, this.serializedFields));

        return comment;
    }
});
