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

    initialize: function() {
        _super(this).initialize.call(this);

        this.on(
            'change:x change:y change:width change:height',
            this._onChangeBounds,
            this
        );
    },

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
    },

    canUpdateBounds: function() {
        return _.isEmpty(this.get('serializedComments'));
    },

    /*
     * Updates underlying model's dimension, when the view's dimension
     * changes.
     */
    _onChangeBounds: function() {
        var draftComment = this.get('draftComment');
        draftComment.ready({
            ready: function() {
                var extraData = draftComment.get('extraData');
                extraData.x = this.get('x');
                extraData.y = this.get('y');
                extraData.width = this.get('width');
                extraData.height = this.get('height');
            }
        }, this);
    },

    saveDraftCommentBounds: function() {
        var draftComment = this.get('draftComment');
        draftComment.ready({
            ready: function() {
                draftComment.save({
                    attrs: [
                        'extra_data.x',
                        'extra_data.y',
                        'extra_data.width',
                        'extra_data.height'
                    ],
                    boundsUpdated: true
                });
            }
        }, this);
    }
});

