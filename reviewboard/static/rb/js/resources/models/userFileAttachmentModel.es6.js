/**
 * A new or existing user file attachment.
 *
 * Model Attributes:
 *     caption (string):
 *         The file attachment's caption.
 *
 *     userName (string):
 *         The username of the owner of the file attachment.
 *
 *     downloadURL (string):
 *         The URL to download the file, for existing file attachments.
 *
 *     file (file):
 *         The file to upload. Only works for newly created
 *         UserFileAttachments.
 *
 *     filename (string):
 *         The name of the file, for existing file attachments.
 */
RB.UserFileAttachment = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            caption: null,
            userName: '',
            downloadURL: null,
            file: null,
            filename: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'user_file_attachment',
    payloadFileKeys: ['path'],

    attrToJsonMap: {
        downloadURL: 'absolute_url',
        file: 'path'
    },

    serializedAttrs: [
        'caption',
        'file'
    ],

    deserializedAttrs: [
        'caption',
        'downloadURL',
        'filename'
    ],

    serializers: {
        file: RB.JSONSerializers.onlyIfValue
    },

    /**
     * Return the URL to use for syncing the model.
     *
     * Returns:
     *     string:
     *     The URL for the resource.
     */
    url() {
        const username = this.get('userName');
        const url = `${SITE_ROOT}api/users/${username}/user-file-attachments/`;

        return this.isNew() ? url : `${url}${this.id}/`;
    }
});
