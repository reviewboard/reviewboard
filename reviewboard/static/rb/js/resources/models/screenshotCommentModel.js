(function() {


var parentProto = RB.BaseComment.prototype;


RB.ScreenshotComment = RB.BaseComment.extend({
    defaults: function() {
        return _.defaults({
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
        }, parentProto.defaults());
    },

    rspNamespace: 'screenshot_comment',
    expandedFields: ['screenshot'],

    attrToJsonMap: _.defaults({
        width: 'w',
        height: 'h',
        thumbnailURL: 'thumbnail_url',
        screenshotID: 'screenshot_id'
    }, parentProto.attrToJsonMap),

    serializedAttrs: [
        'x',
        'y',
        'width',
        'height',
        'screenshotID'
    ].concat(parentProto.serializedAttrs),

    deserializedAttrs: [
        'x',
        'y',
        'width',
        'height',
        'thumbnailURL'
    ].concat(parentProto.deserializedAttrs),

    serializers: _.defaults({
        screenshotID: RB.JSONSerializers.onlyIfUnloaded
    }, parentProto.serializers),

    /*
     * Deserializes comment data from an API payload.
     */
    parseResourceData: function(rsp) {
        var result = parentProto.parseResourceData.call(this, rsp);

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

        return parentProto.validate.call(this, attrs, options);
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


})();
