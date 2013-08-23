RB.FileAttachmentComment = RB.BaseComment.extend({
    defaults: _.defaults({
        /*
         * The ID of the file attachment that fileAttachmentID is diffed
         * against.
         */
        diffAgainstFileAttachmentID: null,

        /* Any extra custom data stored along with the comment. */
        extraData: {},

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
         * The URL for the review UI for the comment on this file attachment.
         */
        reviewURL: null,

        /* The HTML representing a thumbnail, if any, for this comment. */
        thumbnailHTML: null
    }, RB.BaseComment.prototype.defaults),

    rspNamespace: 'file_attachment_comment',
    expandedFields: ['diff_against_file_attachment', 'file_attachment'],

    /*
     * Serializes the comment to a payload that can be sent to the server.
     */
    toJSON: function() {
        var data = RB.BaseComment.prototype.toJSON.call(this);

        _.each(this.get('extraData') || {}, function(value, key) {
            data['extra_data.' + key] = value;
        });

        if (!this.get('loaded')) {
            data.file_attachment_id = this.get('fileAttachmentID');
            data.diff_against_file_attachment_id =
                this.get('diffAgainstFileAttachmentID') || undefined;
        }

        return data;
    },

    /*
     * Deserializes comment data from an API payload.
     */
    parseResourceData: function(rsp) {
        var result = RB.BaseComment.prototype.parseResourceData.call(this,
                                                                     rsp);

        result.extraData = rsp.extra_data;
        result.linkText = rsp.link_text;
        result.thumbnailHTML = rsp.thumbnail_html;
        result.reviewURL = rsp.review_url;
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
     * This will check the file attachment ID and contents of extraData,
     * along with the default comment validation.
     */
    validate: function(attrs, options) {
        var strings = RB.FileAttachmentComment.strings,
            value,
            key;

        if (_.has(attrs, 'fileAttachmentID') && !attrs.fileAttachmentID) {
            return strings.INVALID_FILE_ATTACHMENT_ID;
        }

        if (attrs.extraData !== undefined) {
            if (!_.isObject(attrs.extraData)) {
                return strings.INVALID_EXTRADATA_TYPE;
            }

            for (key in attrs.extraData) {
                if (attrs.extraData.hasOwnProperty(key)) {
                    value = attrs.extraData[key];

                    if (!_.isNull(value) &&
                        (!_.isNumber(value) || _.isNaN(value)) &&
                        !_.isBoolean(value) &&
                        !_.isString(value)) {
                        return strings.INVALID_EXTRADATA_VALUE_TYPE
                            .replace('{key}', key);
                    }
                }
            }
        }

        return RB.BaseComment.prototype.validate.call(this, attrs, options);
    }
}, {
    strings: {
        INVALID_FILE_ATTACHMENT_ID: 'fileAttachmentID must be a valid ID',
        INVALID_EXTRADATA_TYPE:
            'extraData must be an object, null, or undefined',
        INVALID_EXTRADATA_VALUE_TYPE:
            'extraData.{key} must be null, a number, boolean, or string'
    }
});
