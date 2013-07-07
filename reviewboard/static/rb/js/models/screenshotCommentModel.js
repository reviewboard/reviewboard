RB.ScreenshotComment = RB.BaseComment.extend({
    defaults: _.defaults({
        /* The X coordinate for the top-left of the comment region. */
        x: null,

        /* The Y coordinate for the top-left of the comment region. */
        y: null,

        /* The width of the comment region. */
        width: null,

        /* The height of the comment region. */
        height: null,

        /* The ID of the screenshot the comment is on. */
        screenshotID: null,

        /* The screenshot the comment is on. */
        screenshot: null,

        /* The URL to an image depicting what was commented on. */
        thumbnailURL: null
    }, RB.BaseComment.prototype.defaults),

    rspNamespace: 'screenshot_comment',
    expandedFields: ['screenshot'],

    /*
     * Serializes the comment to a payload that can be sent to the server.
     */
    toJSON: function() {
        var data = RB.BaseComment.prototype.toJSON.call(this);

        data.x = this.get('x');
        data.y = this.get('y');
        data.w = this.get('width');
        data.h = this.get('height');

        if (!this.get('loaded')) {
            data.screenshot_id = this.get('screenshotID');
        }

        return data;
    },

    /*
     * Deserializes comment data from an API payload.
     */
    parseResourceData: function(rsp) {
        var result = RB.BaseComment.prototype.parseResourceData.call(this,
                                                                     rsp);

        result.x = rsp.x;
        result.y = rsp.y;
        result.width = rsp.w;
        result.height = rsp.h;
        result.thumbnailURL = rsp.thumbnail_url;
        result.screenshot = new RB.Screenshot(rsp.screenshot, {
            parse: true
        });
        result.screenshotID = result.screenshot.id;

        return result;
    },

    /*
     * Performs validation on the attributes of the model.
     *
     * This will check the screenshot ID and the region of the comment,
     * along with the default comment validation.
     */
    validate: function(attrs, options) {
        var strings = RB.ScreenshotComment.strings;

        if (_.has(attrs, 'screenshotID') && !attrs.screenshotID) {
            return strings.INVALID_SCREENSHOT_ID;
        }

        if (_.has(attrs, 'x') && attrs.x < 0) {
            return strings.INVALID_X;
        }

        if (_.has(attrs, 'y') && attrs.y < 0) {
            return strings.INVALID_Y;
        }

        if (_.has(attrs, 'width') && attrs.width <= 0) {
            return strings.INVALID_WIDTH;
        }

        if (_.has(attrs, 'height') && attrs.height <= 0) {
            return strings.INVALID_HEIGHT;
        }

        return RB.BaseComment.prototype.validate.call(this, attrs, options);
    }
}, {
    strings: {
        INVALID_SCREENSHOT_ID: 'screenshotID must be a valid ID',
        INVALID_X: 'x must be >= 0',
        INVALID_Y: 'y must be >= 0',
        INVALID_WIDTH: 'width must be > 0',
        INVALID_HEIGHT: 'height must be > 0'
    }
});
