/*
 * Reviews.
 *
 * This corresponds to a top-level review. Replies are encapsulated in
 * RB.ReviewReply.
 */
RB.Review = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            /*
             * The text format type to request for text in all responses.
             */
            forceTextType: null,

            shipIt: false,
            'public': false,
            bodyTop: null,
            bodyTopRichText: false,
            bodyBottom: null,
            bodyBottomRichText: false,
            draftReply: null,

            /*
             * A string containing a comma-separated list of text types to include
             * in the payload.
             */
            includeTextTypes: null,

            /*
             * Raw text fields, if forceTextType is used and the caller
             * fetches or posts with includeTextTypes="raw".
             */
            rawTextFields: {},

            timestamp: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'review',

    attrToJsonMap: {
        bodyBottom: 'body_bottom',
        bodyBottomRichText: 'body_bottom_text_type',
        bodyTop: 'body_top',
        bodyTopRichText: 'body_top_text_type',
        forceTextType: 'force_text_type',
        includeTextTypes: 'include_text_types',
        shipIt: 'ship_it'
    },

    serializedAttrs: [
        'forceTextType',
        'includeTextTypes',
        'shipIt',
        'bodyTop',
        'bodyTopRichText',
        'bodyBottom',
        'bodyBottomRichText',
        'public'
    ],

    deserializedAttrs: [
        'shipIt',
        'bodyTop',
        'bodyBottom',
        'public',
        'timestamp'
    ],

    serializers: {
        forceTextType: RB.JSONSerializers.onlyIfValue,
        includeTextTypes: RB.JSONSerializers.onlyIfValue,
        bodyTopRichText: RB.JSONSerializers.textType,
        bodyBottomRichText: RB.JSONSerializers.textType,

        'public': function(value) {
            return value ? 1 : undefined;
        }
    },

    supportsExtraData: true,

    parseResourceData: function(rsp) {
        var rawTextFields = rsp.raw_text_fields || rsp,
            data = RB.BaseResource.prototype.parseResourceData.call(this, rsp);

        data.bodyTopRichText =
            (rawTextFields.body_top_text_type === 'markdown');
        data.bodyBottomRichText =
            (rawTextFields.body_bottom_text_type === 'markdown');

        if (rsp.raw_text_fields) {
            data.rawTextFields = {
                bodyBottom: rsp.raw_text_fields.body_bottom,
                bodyTop: rsp.raw_text_fields.body_top
            };
        }

        return data;
    },

    createDiffComment: function(id, fileDiffID, interFileDiffID, beginLineNum,
                                endLineNum) {
        return new RB.DiffComment({
            parentObject: this,
            id: id,
            fileDiffID: fileDiffID,
            interFileDiffID: interFileDiffID,
            beginLineNum: beginLineNum,
            endLineNum: endLineNum
        });
    },

    createScreenshotComment: function(id, screenshot_id, x, y, width, height) {
        return new RB.ScreenshotComment({
            parentObject: this,
            id: id,
            screenshotID: screenshot_id,
            x: x,
            y: y,
            width: width,
            height: height
        });
    },

    createFileAttachmentComment: function(id, fileAttachmentID,
                                          diffAgainstFileAttachmentID) {
        return new RB.FileAttachmentComment({
            parentObject: this,
            id: id,
            fileAttachmentID: fileAttachmentID,
            diffAgainstFileAttachmentID: diffAgainstFileAttachmentID
        });
    },

    createReply: function() {
        var draftReply = this.get('draftReply');

        if (draftReply === null) {
            draftReply = new RB.ReviewReply({
                parentObject: this
            });
            this.set('draftReply', draftReply);

            draftReply.once('published', function() {
                var reviewRequest = this.get('parentObject');

                reviewRequest.markUpdated(draftReply.get('timestamp'));
                this.set('draftReply', null);
            }, this);
        }

        return draftReply;
    }
});
