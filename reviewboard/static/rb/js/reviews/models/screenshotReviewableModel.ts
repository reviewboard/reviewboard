/**
 * Provides review capabilities for screenshots.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    type AbstractReviewableAttrs,
    AbstractReviewable,
} from './abstractReviewableModel';
import { type SerializedRegionComment } from './commentData';
import { ScreenshotCommentBlock } from './screenshotCommentBlockModel';


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
    static defaults: Partial<Result<ScreenshotReviewableAttrs>> = {
        caption: '',
        imageURL: '',
        screenshotID: null,
    };

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
        serializedCommentBlock: SerializedRegionComment[],
    ) {
        this.createCommentBlock({
            height: serializedCommentBlock[0].height,
            screenshotID: this.get('screenshotID'),
            serializedComments: serializedCommentBlock,
            width: serializedCommentBlock[0].width,
            x: serializedCommentBlock[0].x,
            y: serializedCommentBlock[0].y,
        });
    }
}
