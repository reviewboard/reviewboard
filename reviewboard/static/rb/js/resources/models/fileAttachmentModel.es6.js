/**
 * A new or existing file attachment.
 *
 * Model Attributes:
 *     attachmentHistoryID (number):
 *         The ID of the file attachment's history.
 *
 *     caption (string):
 *         The file attachment's caption.
 *
 *     downloadURL (string):
 *         The URL to download an existing file attachment.
 *
 *     file (file):
 *         The file to upload. Only works for newly created FileAttachments.
 *
 *     filename (string):
 *         The name of the file, for existing file attachments.
 *
 *     reviewURL (string):
 *         The URL to the review UI for this file attachment.
 *
 *     revision (number):
 *         The revision of the file attachment.
 *
 *     thumbnailHTML (string):
 *         The HTML for the thumbnail depicting this file attachment.
 */
RB.FileAttachment = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            attachmentHistoryID: null,
            caption: null,
            downloadURL: null,
            file: null,
            filename: null,
            reviewURL: null,
            revision: null,
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
