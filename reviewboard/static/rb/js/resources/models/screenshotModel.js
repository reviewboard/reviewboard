/*
 * Screenshots.
 */
RB.Screenshot = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            /* The screenshot's optional caption. */
            caption: null,

            /* The screenshot's filename. */
            filename: null,

            /* The URL where the screenshot can be reviewed. */
            reviewURL: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'screenshot',

    attrToJsonMap: {
        reviewURL: 'review_url'
    },

    serializedAttrs: ['caption'],
    deserializedAttrs: ['caption', 'filename', 'reviewURL'],

    /*
     * Returns a displayable name for the screenshot.
     *
     * This will return the caption, if one is set. Otherwise, the filename
     * is returned.
     */
    getDisplayName: function() {
        return this.get('caption') || this.get('filename');
    }
});
