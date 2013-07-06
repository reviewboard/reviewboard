/*
 * Screenshots.
 */
RB.Screenshot = RB.BaseResource.extend({
    defaults: _.defaults({
        /* The screenshot's optional caption. */
        caption: null,

        /* The screenshot's filename. */
        filename: null,

        /* The URL where the screenshot can be reviewed. */
        reviewURL: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'screenshot',

    /*
     * Returns a displayable name for the screenshot.
     *
     * This will return the caption, if one is set. Otherwise, the filename
     * is returned.
     */
    getDisplayName: function() {
        return this.get('caption') || this.get('filename');
    },

    /*
     * Deserializes screenshot data from an API payload.
     */
    parseResourceData: function(rsp) {
        return {
            caption: rsp.caption,
            filename: rsp.filename,
            reviewURL: rsp.review_url
        };
    },

    toJSON: function() {
        return {
            caption: this.get('caption')
        };
    }
});
