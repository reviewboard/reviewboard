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
        bodyTop: null,
        bodyBottom: null,
        draftReply: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'review',

    toJSON: function() {
        var data = {
            ship_it: (this.get('shipIt') ? 1 : 0),
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
            public: rsp.public
        };
    },

    createDiffComment: function(id, filediff, interfilediff, beginLineNum,
                                endLineNum) {
        return new RB.DiffComment({
            parentObject: this,
            id: id,
            fileDiffID: filediff ? filediff.id : null,
            interFileDiffID: interfilediff ? interfilediff.id : null,
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

    createFileAttachmentComment: function(id, file_attachment_id) {
        return new RB.FileAttachmentComment({
            parentObject: this,
            id: id,
            fileAttachmentID: file_attachment_id
        });
    },

    createReply: function() {
        var draftReply = this.get('draftReply');

        if (draftReply === null) {
            draftReply = new RB.ReviewReply({
                parentObject: this
            });
            this.set('draftReply', draftReply);
        }

        return draftReply;
    }
});
