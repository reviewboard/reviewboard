/**
 * A comment on a file attachment.
 *
 * Model Attributes:
 *     diffAgainstFileAttachmentID (number):
 *         The ID of the file attachment that is the "new" side of a comment on
 *         a file diff.
 *
 *     diffAgainstFileAttachment (RB.FileAttachment):
 *         The file attachment that is the "new" side of a comment on a file
 *         diff.
 *
 *     fileAttachmentID (number):
 *         The ID of the file attachment that the comment is on, or the ID of
 *         the file attachment that is the "old" side of a comment on a file
 *         diff.
 *
 *     fileAttachment (RB.FileAttachment):
 *         The file attachment that the comment is on, or the ID of the file
 *         attachment that is the "old" side of a comment on a file diff.
 *
 *     linkText (string):
 *         The text used to describe a link to the file. This may differ
 *         depending on the comment.
 *
 *     reviewURL (string):
 *         The URL for the file attachment review UI for the comment.
 *
 *     thumbnailHTML (string):
 *         The HTML representing a thumbnail, if any, for this comment.
 */
RB.FileAttachmentComment = RB.BaseComment.extend({
    defaults: _.defaults({
        diffAgainstFileAttachmentID: null,
        diffAgainstFileAttachment: null,
        fileAttachmentID: null,
        fileAttachment: null,
        linkText: null,
        reviewURL: null,
        thumbnailHTML: null
    }, RB.BaseComment.prototype.defaults()),

    rspNamespace: 'file_attachment_comment',
    expandedFields: ['diff_against_file_attachment', 'file_attachment'],

    attrToJsonMap: _.defaults({
        diffAgainstFileAttachmentID: 'diff_against_file_attachment_id',
        fileAttachmentID: 'file_attachment_id',
        linkText: 'link_text',
        reviewURL: 'review_url',
        thumbnailHTML: 'thumbnail_html'
    }, RB.BaseComment.prototype.attrToJsonMap),

    serializedAttrs: [
        'diffAgainstFileAttachmentID',
        'fileAttachmentID'
    ].concat(RB.BaseComment.prototype.serializedAttrs),

    deserializedAttrs: [
        'linkText',
        'thumbnailHTML',
        'reviewURL'
    ].concat(RB.BaseComment.prototype.deserializedAttrs),

    serializers: _.defaults({
        fileAttachmentID: RB.JSONSerializers.onlyIfUnloaded,
        diffAgainstFileAttachmentID: RB.JSONSerializers.onlyIfUnloadedAndValue
    }, RB.BaseComment.prototype.serializers),

    /**
     * Deserialize comment data from an API payload.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(rsp) {
        const result = RB.BaseComment.prototype.parseResourceData.call(
            this, rsp);

        result.fileAttachment = new RB.FileAttachment(rsp.file_attachment, {
            parse: true
        });
        result.fileAttachmentID = result.fileAttachment.id;

        if (rsp.diff_against_file_attachment) {
            result.diffAgainstFileAttachment = new RB.FileAttachment(
                rsp.diff_against_file_attachment, {
                    parse: true
                });

            result.diffAgainstFileAttachmentID =
                result.diffAgainstFileAttachment.id;
        }

        return result;
    },

    /**
     * Perform validation on the attributes of the model.
     *
     * This will check the file attachment ID along with the default
     * comment validation.
     *
     * Args:
     *     attrs (object):
     *         Model attributes to validate.
     *
     *     options (object):
     *         Additional options for the operation.
     *
     * Returns:
     *     string:
     *     An error string, if appropriate.
     */
    validate(attrs, options) {
        if (_.has(attrs, 'fileAttachmentID') && !attrs.fileAttachmentID) {
            return RB.FileAttachmentComment.strings.INVALID_FILE_ATTACHMENT_ID;
        }

        return _super(this).validate.call(this, attrs, options);
    }
}, {
    strings: {
        INVALID_FILE_ATTACHMENT_ID: 'fileAttachmentID must be a valid ID'
    }
});
