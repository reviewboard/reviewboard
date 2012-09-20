/*
 * Provides a visual region over an image or other document showing comments.
 *
 * This will show a selection rectangle over part of an image or other
 * content indicating there are comments there. It will also show the
 * number of comments, along with a tooltip showing comment summaries.
 *
 * This is meant to be used with a RegionCommentBlock model.
 */
RB.RegionCommentBlockView = RB.AbstractCommentBlockView.extend({
    className: 'selection',

    /*
     * Initializes RegionCommentBlockView.
     */
    initialize: function() {
        this.on('change:x change:y change:width change:height',
                this._updateDimensions, this);
    },

    /*
     * Renders the comment block.
     *
     * Along with the block's rectangle, a floating tooltip will also be
     * created that displays summaries of the comments.
     *
     * After rendering, the block's style and count will be updated whenever
     * the appropriate state is changed in the model.
     */
    renderContent: function() {
        this._updateDimensions();

        this._$flag = $('<div/>')
            .addClass('selection-flag')
            .appendTo(this.$el);

        this.model.on('change:count', this._updateCount, this);
        this._updateCount();
    },

    /*
     * Positions the comment dlg to the side of the flag.
     */
    positionCommentDlg: function(commentDlg) {
        commentDlg.positionToSide(this._$flag, {
            side: 'b',
            fitOnScreen: true
        });
    },

    /*
     * Updates the position and size of the comment block.
     *
     * The new position and size will reflect the x, y, width, and height
     * properties in the model.
     */
    _updateDimensions: function() {
        var model = this.model;

        this.$el
            .move(model.get('x'), model.get('y'), 'absolute')
            .width(model.get('width'))
            .height(model.get('height'));
    },

    /*
     * Updates the displayed count of comments.
     */
    _updateCount: function() {
        this._$flag.text(this.model.get('count'));
    }
});
