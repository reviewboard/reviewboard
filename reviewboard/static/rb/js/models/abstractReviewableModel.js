/*
 * Abstract model for reviewable content.
 *
 * This is the basis for subclasses that handle review capabilities for
 * some form of content, such as a file attachment.
 *
 * All subclasses must provide a 'commentBlockModel' object type and an
 * addCommentBlocks() function.
 */
RB.AbstractReviewable = Backbone.Model.extend({
    defaults: {
        serializedComments: []
    },

    /*
     * The AbstractCommentBlock subclass for this content type's comment
     * blocks.
     */
    commentBlockModel: null,

    /*
     * Initializes the reviewable.
     */
    initialize: function() {
        console.assert(this.commentBlockModel,
                       'commentBlockModel must be defined');

        this.commentBlocks = new Backbone.Collection();
        this.commentBlocks.model = this.commentBlockModel;

        /* Add all existing comment regions to the page. */
        _.each(this.get('serializedComments'), this.addCommentBlocks, this);
    },

    /*
     * Adds comment blocks for each serialized comment.
     *
     * This must be implemented by subclasses.
     */
    addCommentBlocks: function(serializedComment) {
        console.assert(false, 'This must be implemented by a subclass');
    }
});
