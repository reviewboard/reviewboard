/**
 * A screenshot.
 *
 * Model Attributes:
 *     caption (string):
 *         The screenshot's caption.
 *
 *     filename (string):
 *         The name of the file for the screenshot.
 *
 *     reviewURL (string):
 *         The URL of the review UI for this screenshot.
 */
RB.Screenshot = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            caption: null,
            filename: null,
            reviewURL: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'screenshot',

    attrToJsonMap: {
        reviewURL: 'review_url'
    },

    serializedAttrs: ['caption'],
    deserializedAttrs: ['caption', 'filename', 'reviewURL'],

    /**
     * Return a displayable name for the screenshot.
     *
     * This will return the caption, if one is set. Otherwise, the filename
     * is returned.
     *
     * Returns:
     *     string:
     *     A string to show in the UI.
     */
    getDisplayName() {
        return this.get('caption') || this.get('filename');
    }
});
