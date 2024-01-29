/**
 * Abstract model for reviewable content.
 */

import {
    BaseModel,
    Collection,
    ModelAttributes,
    spina,
} from '@beanbag/spina';

import {
    Review,
    ReviewRequest,
} from 'reviewboard/common';
import {
    AbstractCommentBlock,
    SerializedComment,
} from './abstractCommentBlockModel';


/**
 * Attributes for the AbstractReviewable model.
 *
 * Version Added:
 *     7.0
 */
export interface AbstractReviewableAttrs extends ModelAttributes {
    /** The caption for the item being reviewed. */
    caption: string;

    /** Whether the review UI is rendered inline. */
    renderedInline: boolean;

    /** The review request. */
    reviewRequest: ReviewRequest;

    /** The current review object. */
    review: Review;

    /** The set of serialized comment threads. */
    serializedCommentBlocks: SerializedComment[];
}


/**
 * Abstract model for reviewable content.
 *
 * This is the basis for subclasses that handle review capabilities for
 * some form of content, such as a file attachment.
 *
 * All subclasses must provide a 'commentBlockModel' object type and an
 * loadSerializedCommentBlock() function.
 *
 * Model Attributes:
 *     caption (string):
 *         The caption of the reviewed object, if any.
 *
 *     renderedInline (boolean):
 *         Whether or not the comment is rendered inline.
 *
 *     reviewRequest (RB.ReviewRequest):
 *         The review request that the object being reviewed is associated
 *         with.
 *
 *     review (RB.Review):
 *         The current review that new comments will be added to.
 *
 *     serializedCommentBlocks (Array of object):
 *         Serialized comment blocks.
 */
@spina({
    prototypeAttrs: ['commentBlockModel', 'defaultCommentBlockFields'],
})
export class AbstractReviewable<
    TAttributes extends AbstractReviewableAttrs = AbstractReviewableAttrs,
    TCommentBlockType extends AbstractCommentBlock = null
> extends BaseModel<TAttributes> {
    static defaults: AbstractReviewableAttrs = {
        caption: null,
        renderedInline: false,
        review: null,
        reviewRequest: null,
        serializedCommentBlocks: [],
    };

    /**
     * The list of fields from this model to populate in each new instance
     * of a commentBlockModel.
     *
     * This can also be a function, if anything more custom is required.
     */
    static defaultCommentBlockFields: string[] = [];

    /**********************
     * Instance variables *
     **********************/

    /**
     * The AbstractCommentBlock subclass for this content type's comment
     * blocks.
     */
    static commentBlockModel = null;

    /**
     * The collection of comment blocks.
     */
    commentBlocks: Collection<TCommentBlockType>;

    /**
     * Initialize the reviewable.
     */
    initialize() {
        const reviewRequest = this.get('reviewRequest');

        console.assert(!!this.commentBlockModel,
                       "'commentBlockModel' must be defined in the " +
                       "reviewable's object definition");
        console.assert(!!reviewRequest,
                       '"reviewRequest" must be provided when constructing ' +
                       'the reviewable');

        if (!this.get('review')) {
            this.set('review', reviewRequest.createReview());
        }

        this.commentBlocks = new Collection<TCommentBlockType>([], {
            model: this.commentBlockModel,
        });

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
    }

    /**
     * Create a CommentBlock for this reviewable.
     *
     * The CommentBlock will be stored in the list of comment blocks.
     *
     * Args:
     *     attrs (object):
     *         The attributes for the comment block;
     */
    createCommentBlock(attrs: unknown) {
        this.commentBlocks.add(_.defaults({
            review: this.get('review'),
            reviewRequest: this.get('reviewRequest'),
        }, attrs));
    }

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
    loadSerializedCommentBlock(serializedCommentBlock: SerializedComment) {
        console.assert(false, 'loadSerializedCommentBlock must be ' +
                              'implemented by a subclass');
    }
}
