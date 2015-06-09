(function() {


var parentProto = RB.BaseComment.prototype;


RB.FileAttachmentComment = RB.BaseComment.extend({
    defaults: function() {
         return _.defaults({
            /*
             * The ID of the file attachment that fileAttachmentID is diffed
             * against.
             */
            diffAgainstFileAttachmentID: null,

            /* The ID of the file attachment the comment is on. */
            fileAttachmentID: null,

            /* The file attachment the comment is on. */
            fileAttachment: null,

            /*
             * The text used to describe a link to the file. This may differ
             * depending on the comment.
             */
            linkText: null,

            /*
             * The URL for the review UI for the comment on this file
             * attachment.
             */
            reviewURL: null,

            /* The HTML representing a thumbnail, if any, for this comment. */
            thumbnailHTML: null
        }, parentProto.defaults());
    },

    rspNamespace: 'file_attachment_comment',
    expandedFields: ['diff_against_file_attachment', 'file_attachment'],

    attrToJsonMap: _.defaults({
        diffAgainstFileAttachmentID: 'diff_against_file_attachment_id',
        fileAttachmentID: 'file_attachment_id',
        linkText: 'link_text',
        reviewURL: 'review_url',
        thumbnailHTML: 'thumbnail_html'
    }, parentProto.attrToJsonMap),

    serializedAttrs: [
        'diffAgainstFileAttachmentID',
        'fileAttachmentID'
    ].concat(parentProto.serializedAttrs),

    deserializedAttrs: [
        'linkText',
        'thumbnailHTML',
        'reviewURL'
    ].concat(parentProto.deserializedAttrs),

    serializers: _.defaults({
        fileAttachmentID: RB.JSONSerializers.onlyIfUnloaded,
        diffAgainstFileAttachmentID: RB.JSONSerializers.onlyIfUnloadedAndValue
    }, parentProto.serializers),

    /*
     * Deserializes comment data from an API payload.
     */
    parseResourceData: function(rsp) {
        var result = parentProto.parseResourceData.call(this, rsp);

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

    /*
     * Performs validation on the attributes of the model.
     *
     * This will check the file attachment ID along with the default
     * comment validation.
     */
    validate: function(attrs, options) {
        var strings = RB.FileAttachmentComment.strings;

        if (_.has(attrs, 'fileAttachmentID') && !attrs.fileAttachmentID) {
            return strings.INVALID_FILE_ATTACHMENT_ID;
        }

        return _super(this).validate.call(this, attrs, options);
    }
}, {
    strings: {
        INVALID_FILE_ATTACHMENT_ID: 'fileAttachmentID must be a valid ID'
    }
});


})();
