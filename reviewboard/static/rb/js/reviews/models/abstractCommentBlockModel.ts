/**
 * Represents a region of reviewable content that contains comments.
 */

import {
    type ModelAttributes,
    type Result,
    BaseModel,
    spina,
} from '@beanbag/spina';

import {
    type BaseComment,
    type Review,
    type ReviewRequest,
} from 'reviewboard/common';
import {
    type BaseCommentAttrs,
} from 'reviewboard/common/resources/models/baseCommentModel';
import { type SerializedComment } from './commentData';


/**
 * Attributes for the AbstractCommentBlock model.
 *
 * Version Added:
 *     7.0
 */
export interface AbstractCommentBlockAttrs extends ModelAttributes {
    /** Whether or not the comment can be deleted. */
    canDelete: boolean;

    /** The total number of comments, including a draft comment. */
    count: number;

    /** The draft comment that this block is associated with. */
    draftComment: BaseComment;

    /** Whether or not the review request has a draft. */
    hasDraft: boolean;

    /** The review that the associated comment is a part of. */
    review: Review;

    /** The review request that this comment is on. */
    reviewRequest: ReviewRequest;

    /** An array of serialized comments for display. */
    serializedComments: SerializedComment[];
}


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
 */
@spina({
    prototypeAttrs: ['serializedFields'],
})
export class AbstractCommentBlock<
    TAttributes extends AbstractCommentBlockAttrs
        = AbstractCommentBlockAttrs
> extends BaseModel<TAttributes> {
    /** Default values for the model attributes. */
    static defaults(): Result<Partial<AbstractCommentBlockAttrs>> {
        return {
            canDelete: false,
            count: 0,
            draftComment: null,
            hasDraft: false,
            review: null,
            reviewRequest: null,
            serializedComments: [],
        };
    }

    /**
     * The list of extra fields on this model.
     *
     * These will be stored on the server in the comment's extra_data field.
     */
    static serializedFields: string[] = [];

    /**
     * Initialize the AbstractCommentBlock.
     */
    initialize() {
        console.assert(!!this.get('reviewRequest'),
                       'reviewRequest must be provided');
        console.assert(!!this.get('review'),
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
                        html: comment.html,
                        issueOpened: comment.issue_opened,
                        issueStatus: comment.issue_status,
                        richText: comment.rich_text,
                        text: comment.text,
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
    }

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
    isEmpty(): boolean {
        return (this.get('serializedComments').length === 0 &&
                !this.has('draftComment'));
    }

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
    createComment(
        id: number,
    ): BaseComment | null {
        console.assert(false, 'This must be implemented by a subclass');

        return null;
    }

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
    ensureDraftComment(
        id?: number,
        comment_attr?: BaseCommentAttrs,
    ) {
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
    }

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
    }

    /**
     * Return a warning about commenting on a deleted object.
     *
     * Version Added:
     *     6.0
     *
     * Returns:
     *     string:
     *     A warning to display to the user if they're commenting on a deleted
     *     object. Return null if there's no warning.
     */
    getDeletedWarning(): string | null {
        return null;
    }

    /**
     * Return a warning about commenting on a draft object.
     *
     * Returns:
     *     string:
     *     A warning to display to the user if they're commenting on a draft
     *     object. Return null if there's no warning.
     */
    getDraftWarning(): string | null {
        return null;
    }
}
