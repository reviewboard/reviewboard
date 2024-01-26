/**
 * Represents the comments on a region of an image or document.
 */

import { spina } from '@beanbag/spina';

import {
    FileAttachmentCommentBlock,
    FileAttachmentCommentBlockAttrs,
} from './fileAttachmentCommentBlockModel';


/**
 * Attributes for the RegionCommentBlock model.
 *
 * Version Added:
 *     7.0
 */
export interface RegionCommentBlockAttrs
    extends FileAttachmentCommentBlockAttrs {
    /** The height of the region being commented upon. */
    height: number;

    /** The width of the region being commented upon. */
    width: number;

    /** The X position of the region being commented upon. */
    x: number;

    /** The Y position of the region being commented upon. */
    y: number;
}


/**
 * The serialized comment data.
 *
 * Version Added:
 *     7.0
 */
interface SerializedRegionCommentFields {
    height: string;
    width: string;
    x: string;
    y: string;
}


/**
 * Represents the comments on a region of an image or document.
 *
 * RegionCommentBlock deals with creating and representing comments
 * that exist in a specific region of some content.
 *
 * See Also:
 *     :js:class:`RB.FileAttachmentCommentBlock`:
 *         For attributes defined on the base model.
 *
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For attributes defined on all comment block models.
 */
@spina
export class RegionCommentBlock<
    TAttributes extends RegionCommentBlockAttrs = RegionCommentBlockAttrs
> extends FileAttachmentCommentBlock<TAttributes> {
    /** Default values for the model attributes. */
    static defaults: RegionCommentBlockAttrs = _.defaults({
        height: null,
        width: null,
        x: null,
        y: null,
    }, super.defaults);

    static serializedFields = ['x', 'y', 'width', 'height'];

    /**
     * Parse the incoming attributes for the comment block.
     *
     * The fields are stored server-side as strings, so we need to convert
     * them back to integers where appropriate.
     *
     * Args:
     *     fields (object):
     *         The serialized fields for the comment.
     *
     * Returns:
     *     object:
     *     The parsed data.
     */
    parse(
        fields: SerializedRegionCommentFields,
    ): Partial<RegionCommentBlockAttrs> {
        return {
            height: parseInt(fields.height, 10) || undefined,
            width: parseInt(fields.width, 10) || undefined,
            x: parseInt(fields.x, 10) || undefined,
            y: parseInt(fields.y, 10) || undefined,
        };
    }

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
        return _.isEmpty(this.get('serializedComments'));
    }

    /**
     * Save the new bounds of the draft comment to the server.
     *
     * The new bounds will be stored in the comment's ``x``, ``y``,
     * ``width``, and ``height`` keys in ``extra_data``.
     */
    async saveDraftCommentBounds() {
        const draftComment = this.get('draftComment');

        await draftComment.ready();

        const extraData = draftComment.get('extraData');

        extraData.x = this.get('x');
        extraData.y = this.get('y');
        extraData.width = this.get('width');
        extraData.height = this.get('height');

        await draftComment.save({
            attrs: [
                'extra_data.x',
                'extra_data.y',
                'extra_data.width',
                'extra_data.height',
            ],
            boundsUpdated: true,
        });
    }
}
