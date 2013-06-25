/*
 * A new or existing file attachment.
 *
 */
RB.FileAttachment = RB.BaseResource.extend({
    defaults: _.defaults({
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
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'file_attachment',
    payloadFileKeys: ['path'],

    /*
     * Serializes the changes to the file attachment to a payload.
     */
    toJSON: function() {
        var payload = {
            caption: this.get('caption')
        };

        if (this.isNew()) {
            payload.path = this.get('file');
        }

        return payload;
    },

    /*
     * Deserializes a file attachment data from an API payload.
     */
    parseResourceData: function(rsp) {
        return {
            caption: rsp.caption,
            downloadURL: rsp.url,
            filename: rsp.filename,
            iconURL: rsp.icon_url,
            reviewURL: rsp.review_url,
            thumbnailHTML: rsp.thumbnail
        };
    }
});
