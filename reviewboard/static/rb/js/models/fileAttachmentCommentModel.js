RB.FileAttachmentComment = RB.BaseComment.extend({
    defaults: _.defaults({
        /* Any extra custom data stored along with the comment. */
        extraData: {},

        /* The ID of the file attachment the comment is on. */
        fileAttachmentID: null
    }, RB.BaseComment.prototype.defaults),

    rspNamespace: 'file_attachment_comment',

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
        }

        return data;
    },

    /*
     * Deserializes comment data from an API payload.
     */
    parse: function(rsp) {
        var result = RB.BaseComment.prototype.parse.call(this, rsp),
            rspData = rsp[this.rspNamespace];

        result.extraData = rspData.extra_data;

        return result;
    },

    /*
     * Performs validation on the attributes of the model.
     *
     * This will check the file attachment ID and contents of extraData,
     * along with the default comment validation.
     */
    validate: function(attrs, options) {
        var strings = RB.FileAttachmentComment.strings;

        if (_.has(attrs, 'fileAttachmentID') && !attrs.fileAttachmentID) {
            return strings.INVALID_FILE_ATTACHMENT_ID;
        }

        if (attrs.extraData !== undefined) {
            if (!_.isObject(attrs.extraData)) {
                return strings.INVALID_EXTRADATA_TYPE;
            }

            for (key in attrs.extraData) {
                if (attrs.extraData.hasOwnProperty(key)) {
                    var value = attrs.extraData[key];

                    if (!_.isNull(value) &&
                        (!_.isNumber(value) || _.isNaN(value)) &&
                        !_.isBoolean(value) &&
                        !_.isString(value)) {
                        return strings.INVALID_EXTRADATA_VALUE_TYPE
                            .replace('{key}', key)
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
