/**
 * Represents the comments on a region of a screenshot.
 */

import { spina } from '@beanbag/spina';

import {
    type AbstractCommentBlockAttrs,
    AbstractCommentBlock,
} from './abstractCommentBlockModel';


/**
 * Attributes for the ScreenshotCommentBlock model.
 *
 * Version Added:
 *     7.0
 */
export interface ScreenshotCommentBlockAttrs
    extends AbstractCommentBlockAttrs {
    /** The height of the region being commented upon. */
    height: number;

    /** The ID of the screenshot being commented upon. */
    screenshotID: number;

    /** The width of the region being commented upon. */
    width: number;

    /** The X position of the region being commented upon. */
    x: number;

    /** The Y position of the region being commented upon. */
    y: number;
}


/**
 * Represents the comments on a region of a screenshot.
 *
 * ScreenshotCommentBlock deals with creating and representing comments
 * that exist in a specific region of a screenshot.
 *
 * See Also:
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For attributes defined on the base model.
 */
@spina
export class ScreenshotCommentBlock
    extends AbstractCommentBlock<ScreenshotCommentBlockAttrs> {
    /** The default values for the model attributes. */
    static defaults = _.defaults({
        height: null,
        screenshotID: null,
        width: null,
        x: null,
        y: null,
    }, super.defaults);

    /**
     * Return whether the bounds of this region can be updated.
     *
     * If there are any existing published comments on this region, it
     * cannot be updated.
     *
     * Returns:
     *     boolean:
     *     A value indicating whether new bounds can be set for this region.
     */
    canUpdateBounds(): boolean {
        return false;
    }

    /**
     * Creates a ScreenshotComment for the given comment ID.
     *
     * Args:
     *     id (number):
     *         The ID of the comment to instantiate the model for.
     *
     * Returns:
     *     RB.ScreenshotComment:
     *     The new comment model.
     */
    createComment(
        id: number,
    ): RB.ScreenshotComment {
        return this.get('review').createScreenshotComment(
            id, this.get('screenshotID'), this.get('x'), this.get('y'),
            this.get('width'), this.get('height'));
    }
}
