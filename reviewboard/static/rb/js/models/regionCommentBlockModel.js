/*
 * Represents the comments on a region of an image or document.
 *
 * RegionCommentBlock deals with creating and representing comments
 * that exist in a specific region of some content.
 */
RB.RegionCommentBlock = RB.FileAttachmentCommentBlock.extend({
    defaults: _.defaults({
        x: null,
        y: null,
        width: null,
        height: null
    }, RB.AbstractCommentBlock.prototype.defaults),

    serializedFields: ['x', 'y', 'width', 'height'],

    /*
     * Parses the incoming attributes for the comment block.
     *
     * The fields are stored server-side as strings, so we need to convert
     * them back to integers where appropriate.
     */
    parse: function(fields) {
        fields.x = parseInt(fields.x, 10) || undefined;
        fields.y = parseInt(fields.y, 10) || undefined;
        fields.width = parseInt(fields.width, 10) || undefined;
        fields.height = parseInt(fields.height, 10) || undefined;

        return fields;
    }
});

