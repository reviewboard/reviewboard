/**
 * Abstract model for reviewable content.
 */

import {
    type ModelAttributes,
    type Result,
    BaseModel,
    Collection,
    spina,
} from '@beanbag/spina';

import {
    type Review,
    type ReviewRequest,
} from 'reviewboard/common';
import { type AbstractCommentBlock } from './abstractCommentBlockModel';
import { type SerializedComment } from './commentData';


/**
 * The serialized comment block type.
 *
 * Version Added:
 *     7.0
 */
export type SerializedCommentBlocks = { [key: string]: SerializedComment[] };


/**
 * Attributes for the AbstractReviewable model.
 *
 * Version Added:
 *     7.0
 */
export interface AbstractReviewableAttrs extends ModelAttributes {
    /** The caption for the item being reviewed. */
    caption: string;

    /**
     * Whether the review UI is rendered inline.
     */
    renderedInline: boolean;

    /** The review request. */
    reviewRequest: ReviewRequest;

    /** The current review object. */
    review: Review;

    /** The set of serialized comment threads. */
    serializedCommentBlocks: SerializedCommentBlocks;
}


/**
 * Abstract model for reviewable content.
 *
 * This is the basis for subclasses that handle review capabilities for
 * some form of content, such as a file attachment.
 *
 * All subclasses must provide a 'commentBlockModel' object type and an
 * loadSerializedCommentBlock() function.
 */
@spina({
    prototypeAttrs: ['commentBlockModel', 'defaultCommentBlockFields'],
})
export class AbstractReviewable<
    TAttributes extends AbstractReviewableAttrs = AbstractReviewableAttrs,
    TCommentBlockType extends AbstractCommentBlock = null
> extends BaseModel<TAttributes> {
    static defaults(): Result<Partial<AbstractReviewableAttrs>> {
        return {
            caption: null,
            renderedInline: false,
            review: null,
            reviewRequest: null,
            serializedCommentBlocks: {},
        };
    }

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
        const commentBlocks = this.get('serializedCommentBlocks');

        if (commentBlocks !== null) {
            for (const comments of Object.values(commentBlocks)) {
                if (comments.length) {
                    this.loadSerializedCommentBlock(comments);
                }
            }
        }
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
     *     serializedComments (Array of SerializedComment):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(serializedComments: SerializedComment[]) {
        console.assert(false, 'loadSerializedCommentBlock must be ' +
                              'implemented by a subclass');
    }
}
