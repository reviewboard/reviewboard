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
        reviewRequest: null,
        review: null,
        serializedComments: []
    },

    /*
     * The AbstractCommentBlock subclass for this content type's comment
     * blocks.
     */
    commentBlockModel: null,

    /*
     * The list of fields from this model to populate in each new instance
     * of a commentBlockModel.
     *
     * This can also be a function, if anything more custom is required.
     */
    defaultCommentBlockFields: [],

    /*
     * Initializes the reviewable.
     */
    initialize: function() {
        var reviewRequest = this.get('reviewRequest');

        console.assert(this.commentBlockModel,
                       "'commentBlockModel' must be defined in the " +
                       "reviewable's object definition");
        console.assert(reviewRequest,
                       "'reviewRequest' must be provided when constructing " +
                       "the reviewable");

        if (!this.get('review')) {
            this.set('review', reviewRequest.createReview());
        }

        this.commentBlocks = new Backbone.Collection();
        this.commentBlocks.model = this.commentBlockModel;

        /* Add all existing comment regions to the page. */
        _.each(this.get('serializedComments'), this.addCommentBlocks, this);
    },

    /*
     * Creates a CommentBlock for this reviewable.
     *
     * The CommentBlock will be stored in the list of comment blocks.
     */
    createCommentBlock: function(attrs) {
        this.commentBlocks.add(_.defaults({
            reviewRequest: this.get('reviewRequest'),
            review: this.get('review')
        }, attrs));
    },

    /*
     * Adds comment blocks for each serialized comment.
     *
     * This should parse the serializedComment and add one or more
     * comment blocks (using createCommentBlock).
     *
     * This must be implemented by subclasses.
     */
    addCommentBlocks: function(serializedComment) {
        console.assert(false, 'This must be implemented by a subclass');
    }
});
