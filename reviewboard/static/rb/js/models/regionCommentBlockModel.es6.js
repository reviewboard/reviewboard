/**
 * Represents the comments on a region of an image or document.
 *
 * RegionCommentBlock deals with creating and representing comments
 * that exist in a specific region of some content.
 *
 * Model Attributes:
 *     x (number):
 *         The X position of the region being commented upon.
 *
 *     y (number):
 *         The Y position of the region being commented upon.
 *
 *     width (number):
 *         The width of the region being commented upon.
 *
 *     height (number):
 *         The height of the region being commented upon.
 *
 * See Also:
 *     :js:class:`RB.FileAttachmentCommentBlock`:
 *         For attributes defined on the base model.
 *
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For attributes defined on all comment block models.
 */
RB.RegionCommentBlock = RB.FileAttachmentCommentBlock.extend({
    defaults: _.defaults({
        x: null,
        y: null,
        width: null,
        height: null,
    }, RB.AbstractCommentBlock.prototype.defaults),

    serializedFields: ['x', 'y', 'width', 'height'],

    /**
     * Parse the incoming attributes for the comment block.
     *
     * The fields are stored server-side as strings, so we need to convert
     * them back to integers where appropriate.
     *
     * Args:
     *     fields (object):
     *         The serialized fields for the comment.
     *
     * Returns:
     *     object:
     *     The parsed data.
     */
    parse(fields) {
        fields.x = parseInt(fields.x, 10) || undefined;
        fields.y = parseInt(fields.y, 10) || undefined;
        fields.width = parseInt(fields.width, 10) || undefined;
        fields.height = parseInt(fields.height, 10) || undefined;

        return fields;
    },

    /**
     * Return whether the bounds of this region can be updated.
     *
     * If there are any existing published comments on this region, it
     * cannot be updated.
     *
     * Returns:
     *     boolean:
     *     A value indicating whether new bounds can be set for this region.
     */
    canUpdateBounds() {
        return _.isEmpty(this.get('serializedComments'));
    },

    /**
     * Save the new bounds of the draft comment to the server.
     *
     * The new bounds will be stored in the comment's ``x``, ``y``,
     * ``width``, and ``height`` keys in ``extra_data``.
     */
    saveDraftCommentBounds() {
        const draftComment = this.get('draftComment');

        draftComment.ready({
            ready: () => {
                const extraData = draftComment.get('extraData');

                extraData.x = this.get('x');
                extraData.y = this.get('y');
                extraData.width = this.get('width');
                extraData.height = this.get('height');

                draftComment.save({
                    attrs: [
                        'extra_data.x',
                        'extra_data.y',
                        'extra_data.width',
                        'extra_data.height',
                    ],
                    boundsUpdated: true,
                });
            }
        });
    },
});
