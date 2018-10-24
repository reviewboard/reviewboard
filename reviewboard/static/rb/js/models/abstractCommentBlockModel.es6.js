/**
 * Represents a region of reviewable content that contains comments.
 *
 * This stores all comments that match a given region, as defined by a
 * subclass of AbstractCommentBlock.
 *
 * New draft comments can be created, which will later be stored on the
 * server.
 *
 * The total number of comments in the block (including any draft comment)
 * will be stored, which may be useful for display.
 *
 * Model Attributes:
 *     canDelete (boolean):
 *         Whether or not the comment can be deleted.
 *
 *     count (number):
 *         The total number of comments, including a draft comment.
 *
 *     draftComment (RB.BaseComment):
 *         The draft comment that this block is associated with.
 *
 *     hasDraft (boolean):
 *         Whether or not the review request has a draft.
 *
 *     review (RB.Review):
 *         The review that the associated comment is a part of.
 *
 *     reviewRequest (RB.ReviewRequest):
 *         The review request that this comment is on.
 *
 *     serializedComments (Array of object):
 *         An array of serialized comments for display.
 */
RB.AbstractCommentBlock = Backbone.Model.extend({
    defaults: {
        hasDraft: false,
        canDelete: false,
        draftComment: null,
        reviewRequest: null,
        review: null,
        serializedComments: [],
        count: 0
    },

    /**
     * Initialize the AbstractCommentBlock.
     */
    initialize() {
        console.assert(this.get('reviewRequest'),
                       'reviewRequest must be provided');
        console.assert(this.get('review'),
                       'review must be provided');

        /*
         * Find out if there are any draft comments and filter them out of the
         * stored list of comments.
         */
        const comments = this.get('serializedComments');
        const newSerializedComments = [];

        if (comments.length > 0) {
            comments.forEach(comment => {
                // We load in encoded text, so decode it.
                comment.text = $('<div>').html(comment.text).text();

                if (comment.localdraft) {
                    this.ensureDraftComment(comment.comment_id, {
                        text: comment.text,
                        richText: comment.rich_text,
                        issueOpened: comment.issue_opened,
                        issueStatus: comment.issue_status,
                        html: comment.html,
                    });
                } else {
                    newSerializedComments.push(comment);
                }
            }, this);

            this.set('serializedComments', newSerializedComments);
        } else {
            this.ensureDraftComment();
        }

        this.on('change:draftComment', this._updateCount, this);
        this._updateCount();
    },

    /**
     * Return whether or not the comment block is empty.
     *
     * A comment block is empty if there are no stored comments and no
     * draft comment.
     *
     * Returns:
     *     boolean:
     *     Whether the comment block is empty.
     */
    isEmpty() {
        return (this.get('serializedComments').length === 0 &&
                !this.has('draftComment'));
    },

    /**
     * Create a draft comment, optionally with a given ID and text.
     *
     * This must be implemented by a subclass to return a Comment class
     * specific to the subclass.
     *
     * Args:
     *     id (number):
     *         The ID of the comment to instantiate the model for.
     *
     * Returns:
     *     RB.BaseComment:
     *     The new comment model.
     */
    createComment(id) {
        console.assert(false, 'This must be implemented by a subclass');
    },

    /**
     * Create a draft comment in this comment block.
     *
     * Only one draft comment can exist per block, so if one already exists,
     * this will do nothing.
     *
     * The actual comment object is up to the subclass to create.
     *
     * Args:
     *     id (number):
     *         The ID of the comment.
     *
     *     comment_attr (object):
     *         Attributes to set on the comment model.
     */
    ensureDraftComment(id, comment_attr) {
        if (this.has('draftComment')) {
            return;
        }

        const comment = this.createComment(id);
        comment.set(comment_attr);
        comment.on('saved', this._updateCount, this);
        comment.on('destroy', () => {
            this.set('draftComment', null);
            this._updateCount();
        });

        this.set('draftComment', comment);
    },

    /**
     * Update the displayed number of comments in the comment block.
     *
     * If there's a draft comment, it will be added to the count. Otherwise,
     * this depends solely on the number of published comments.
     */
    _updateCount() {
        let count = this.get('serializedComments').length;

        if (this.has('draftComment')) {
            count++;
        }

        this.set('count', count);
    },
});
