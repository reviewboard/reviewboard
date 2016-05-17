/**
 * A comment on a screenshot.
 *
 * Model Attributes:
 *     x (number):
 *         The X coordinate of the pixel at the top-left of the comment region.
 *
 *     y (number):
 *         The Y coordinate of the pixel at the top-left of the comment region.
 *
 *     width (number):
 *         The width of the comment region, in pixels.
 *
 *     height (number):
 *         The height of the comment region, in pixels.
 *
 *     screenshotID (number):
 *         The ID of the screenshot that this comment is on.
 *
 *     screenshot (RB.Screenshot):
 *         The screenshot that this comment is on.
 *
 *     thumbnailURL (string):
 *         The URL to an image file showing the region of the comment.
 */
RB.ScreenshotComment = RB.BaseComment.extend({
    defaults: _.defaults({
        x: null,
        y: null,
        width: null,
        height: null,
        screenshotID: null,
        screenshot: null,
        thumbnailURL: null
    }, RB.BaseComment.prototype.defaults()),

    rspNamespace: 'screenshot_comment',
    expandedFields: ['screenshot'],

    attrToJsonMap: _.defaults({
        width: 'w',
        height: 'h',
        thumbnailURL: 'thumbnail_url',
        screenshotID: 'screenshot_id'
    }, RB.BaseComment.prototype.attrToJsonMap),

    serializedAttrs: [
        'x',
        'y',
        'width',
        'height',
        'screenshotID'
    ].concat(RB.BaseComment.prototype.serializedAttrs),

    deserializedAttrs: [
        'x',
        'y',
        'width',
        'height',
        'thumbnailURL'
    ].concat(RB.BaseComment.prototype.deserializedAttrs),

    serializers: _.defaults({
        screenshotID: RB.JSONSerializers.onlyIfUnloaded
    }, RB.BaseComment.prototype.serializers),

    /**
     * Deserialize comment data from an API payload.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(rsp) {
        const result = RB.BaseComment.prototype.parseResourceData.call(
            this, rsp);

        result.screenshot = new RB.Screenshot(rsp.screenshot, {
            parse: true
        });
        result.screenshotID = result.screenshot.id;

        return result;
    },

    /*
     * Validate the attributes of the model.
     *
     * This will check the screenshot ID and the region of the comment,
     * along with the default comment validation.
     *
     * Args:
     *     attrs (object):
     *         The model attributes to validate.
     *
     * Returns:
     *     string:
     *     An error string, if appropriate.
     */
    validate(attrs) {
        if (_.has(attrs, 'screenshotID') && !attrs.screenshotID) {
            return RB.ScreenshotComment.strings.INVALID_SCREENSHOT_ID;
        }

        if (_.has(attrs, 'x') && attrs.x < 0) {
            return RB.ScreenshotComment.strings.INVALID_X;
        }

        if (_.has(attrs, 'y') && attrs.y < 0) {
            return RB.ScreenshotComment.strings.INVALID_Y;
        }

        if (_.has(attrs, 'width') && attrs.width <= 0) {
            return RB.ScreenshotComment.strings.INVALID_WIDTH;
        }

        if (_.has(attrs, 'height') && attrs.height <= 0) {
            return RB.ScreenshotComment.strings.INVALID_HEIGHT;
        }

        return RB.BaseComment.prototype.validate.apply(this, arguments);
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
