/**
 * Provides review capabilities for screenshots.
 */

import { spina } from '@beanbag/spina';

import {
    AbstractReviewable,
    type AbstractReviewableAttrs,
} from './abstractReviewableModel';
import type { SerializedComment } from './commentData';
import { ScreenshotCommentBlock } from './screenshotCommentBlockModel';


/**
 * Serialized data for a screenshot comment block.
 *
 * Version Added:
 *     7.0
 */
export interface SerializedScreenshotComment extends SerializedComment {
    x: number;
    y: number;
    w: number;
    h: number;
}


/**
 * Attributes for the ScreenshotReviewable model.
 *
 * Version Added:
 *     7.0
 */
export interface ScreenshotReviewableAttrs extends AbstractReviewableAttrs {
    /** The caption of the screenshot. */
    caption: string;

    /** The URL of the image being reviewed. */
    imageURL: string;

    /** The ID of the screenshot being reviewed. */
    screenshotID: number;
}


/**
 * Provides review capabilities for screenshots.
 *
 * See Also:
 *     :js:class:`RB.AbstractReviewable`:
 *         For the attributes defined by the base model.
 */
@spina
export class ScreenshotReviewable extends AbstractReviewable<
    ScreenshotReviewableAttrs,
    ScreenshotCommentBlock
> {
    static defaults: ScreenshotReviewableAttrs = _.defaults({
        caption: '',
        imageURL: '',
        screenshotID: null,
    }, super.defaults);

    static commentBlockModel = ScreenshotCommentBlock;
    static defaultCommentBlockFields = ['screenshotID'];

    /**
     * Load a serialized comment and add comment blocks for it.
     *
     * Args:
     *     serializedCommentBlock (object):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(
        serializedCommentBlock: SerializedScreenshotComment[],
    ) {
        this.createCommentBlock({
            height: serializedCommentBlock[0].h,
            screenshotID: this.get('screenshotID'),
            serializedComments: serializedCommentBlock,
            width: serializedCommentBlock[0].w,
            x: serializedCommentBlock[0].x,
            y: serializedCommentBlock[0].y,
        });
    }
}
