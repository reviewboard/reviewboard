/*
 * A new or existing file attachment.
 */
RB.FileAttachment = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            /* The file attachment's history ID. */
            attachmentHistoryID: null,
            
            /* The file attachment's caption. */
            caption: null,

            /* The URL to download a file, for existing file attachments. */
            downloadURL: null,

            /* The file to upload. Only works for newly created FileAttachments. */
            file: null,

            /* The name of the file, for existing file attachments. */
            filename: null,

            /* The URL to the review UI for this file attachment. */
            reviewURL: null,

            /* The revision of the file attachment. */
            revision: null,
            
            /* The HTML for the thumbnail depicting this file attachment. */
            thumbnailHTML: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'file_attachment',
    payloadFileKeys: ['path'],

    attrToJsonMap: {
        attachmentHistoryID: 'attachment_history_id',
        downloadURL: 'url',
        file: 'path',
        reviewURL: 'review_url',
        thumbnailHTML: 'thumbnail'
    },

    serializedAttrs: [
        'attachmentHistoryID',
        'caption',
        'file'
    ],

    deserializedAttrs: [
        'attachmentHistoryID',
        'caption',
        'downloadURL',
        'filename',
        'reviewURL',
        'revision',
        'thumbnailHTML'
    ],

    serializers: {
        attachmentHistoryID: RB.JSONSerializers.onlyIfNew,
        file: RB.JSONSerializers.onlyIfNew
    }
});
