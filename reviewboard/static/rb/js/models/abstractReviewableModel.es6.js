/**
 * Abstract model for reviewable content.
 *
 * This is the basis for subclasses that handle review capabilities for
 * some form of content, such as a file attachment.
 *
 * All subclasses must provide a 'commentBlockModel' object type and an
 * loadSerializedCommentBlock() function.
 */
RB.AbstractReviewable = Backbone.Model.extend({
    defaults: {
        caption: null,
        renderedInline: false,
        reviewRequest: null,
        review: null,
        serializedCommentBlocks: [],
    },

    /**
     * The AbstractCommentBlock subclass for this content type's comment
     * blocks.
     */
    commentBlockModel: null,

    /**
     * The list of fields from this model to populate in each new instance
     * of a commentBlockModel.
     *
     * This can also be a function, if anything more custom is required.
     */
    defaultCommentBlockFields: [],

    /**
     * Initialize the reviewable.
     */
    initialize() {
        const reviewRequest = this.get('reviewRequest');

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

        /*
         * Add all existing comment regions to the page.
         *
         * This intentionally doesn't use forEach because some review UIs (such
         * as the image review UI) return their serialized comments as an
         * object instead of an array.
         */
        _.each(this.get('serializedCommentBlocks'),
               this.loadSerializedCommentBlock,
               this);
    },

    /**
     * Create a CommentBlock for this reviewable.
     *
     * The CommentBlock will be stored in the list of comment blocks.
     *
     * Args:
     *     attrs (object):
     *         The attributes for the comment block;
     */
    createCommentBlock(attrs) {
        this.commentBlocks.add(_.defaults({
            reviewRequest: this.get('reviewRequest'),
            review: this.get('review'),
        }, attrs));
    },

    /**
     * Load a serialized comment and add comment blocks for it.
     *
     * This should parse the serializedCommentBlock and add one or more
     * comment blocks (using createCommentBlock).
     *
     * This must be implemented by subclasses.
     *
     * Args:
     *     serializedCommentBlock (object):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(serializedCommentBlock) {
        console.assert(false, 'loadSerializedCommentBlock must be ' +
                              'implemented by a subclass');
    },
});
