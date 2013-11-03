/*
 * Reviews.
 *
 * This corresponds to a top-level review. Replies are encapsulated in
 * RB.ReviewReply.
 */
RB.Review = RB.BaseResource.extend({
    defaults: _.defaults({
        shipIt: false,
        public: false,
        richText: false,
        bodyTop: null,
        bodyBottom: null,
        draftReply: null,
        timestamp: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'review',

    toJSON: function() {
        var data = {
            rich_text: this.get('richText'),
            ship_it: this.get('shipIt'),
            body_top: this.get('bodyTop'),
            body_bottom: this.get('bodyBottom')
        };

        if (this.get('public')) {
            data.public = 1;
        }

        return data;
    },

    parseResourceData: function(rsp) {
        return {
            shipIt: rsp.ship_it,
            bodyTop: rsp.body_top,
            bodyBottom: rsp.body_bottom,
            public: rsp.public,
            richText: rsp.rich_text,
            timestamp: rsp.timestamp
        };
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
