/*
 * Reviews.
 *
 * This corresponds to a top-level review. Replies are encapsulated in
 * RB.ReviewReply.
 */
RB.Review = RB.BaseResource.extend({
    defaults: _.defaults({
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
         * Markdown-formatted text fields, if the caller fetches or posts with
         * with includeTextTypes="markdown".
         */
        markdownTextFields: {},

        /*
         * Raw text fields, if the caller fetches or posts with
         * includeTextTypes="raw".
         */
        rawTextFields: {},

        timestamp: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'review',

    toJSON: function() {
        var data = {
            force_text_type: this.get('forceTextType') || undefined,
            include_text_types: this.get('includeTextTypes') || undefined,
            ship_it: this.get('shipIt'),
            body_top: this.get('bodyTop'),
            body_top_text_type: this.get('bodyTopRichText')
                                ? 'markdown' : 'plain',
            body_bottom: this.get('bodyBottom'),
            body_bottom_text_type: this.get('bodyBottomRichText')
                                   ? 'markdown' : 'plain'
        };

        if (this.get('public')) {
            data['public'] = 1;
        }

        return data;
    },

    parseResourceData: function(rsp) {
        var rawTextFields = rsp.raw_text_fields || rsp;

        var data = {
            shipIt: rsp.ship_it,
            bodyTop: rsp.body_top,
            bodyTopRichText:
                rawTextFields.body_top_text_type === 'markdown',
            bodyBottom: rsp.body_bottom,
            bodyBottomRichText:
                rawTextFields.body_bottom_text_type === 'markdown',
            'public': rsp['public'],
            timestamp: rsp.timestamp
        };

        if (rsp.raw_text_fields) {
            data.rawTextFields = {
                bodyBottom: rsp.raw_text_fields.body_bottom,
                bodyTop: rsp.raw_text_fields.body_top
            };
        }

        if (rsp.markdown_text_fields) {
            data.markdownTextFields = {
                bodyBottom: rsp.markdown_text_fields.body_bottom,
                bodyTop: rsp.markdown_text_fields.body_top
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
