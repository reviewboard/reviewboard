/*
 * A new or existing file attachment.
 */
RB.FileAttachment = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            /* The file attachment's caption. */
            caption: null,

            /* The URL to download a file, for existing file attachments. */
            downloadURL: null,

            /* The file to upload. Only works for newly created FileAttachments. */
            file: null,

            /* The name of the file, for existing file attachments. */
            filename: null,

            /* The URL to an icon for this file type. */
            iconURL: null,

            /* The URL to the review UI for this file attachment. */
            reviewURL: null,

            /* The HTML for the thumbnail depicting this file attachment. */
            thumbnailHTML: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'file_attachment',
    payloadFileKeys: ['path'],

    attrToJsonMap: {
        downloadURL: 'url',
        file: 'path',
        iconURL: 'icon_url',
        reviewURL: 'review_url',
        thumbnailHTML: 'thumbnail'
    },

    serializedAttrs: ['caption', 'file'],

    deserializedAttrs: [
        'caption',
        'downloadURL',
        'filename',
        'iconURL',
        'reviewURL',
        'thumbnailHTML'
    ],

    serializers: {
        file: RB.JSONSerializers.onlyIfNew
    }
});
