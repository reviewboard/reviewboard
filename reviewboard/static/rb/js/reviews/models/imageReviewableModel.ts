/**
 * Provides review capabilities for image file attachments.
 */

import { spina } from '@beanbag/spina';

import {
    FileAttachmentReviewable,
    type FileAttachmentReviewableAttrs,
} from './fileAttachmentReviewableModel';
import { RegionCommentBlock } from './regionCommentBlockModel';


/**
 * Attributes for the ImageReviewable model.
 *
 * Version Added:
 *     7.0
 */
export interface ImageReviewableAttrs extends FileAttachmentReviewableAttrs {
    /** The image URL of the original image in the case of a image diff. */
    diffAgainstimageURL: string;

    /** The image URL. */
    imageURL: string;

    /** The scale at which the image is being rendered.*/
    scale: number;
}


/**
 * Provides review capabilities for image file attachments.
 */
@spina
export class ImageReviewable extends FileAttachmentReviewable<
    ImageReviewableAttrs,
    RegionCommentBlock
> {
    static defaults: ImageReviewableAttrs = _.defaults({
        diffAgainstImageURL: '',
        imageURL: '',
        scale: 1,
    }, super.defaults);

    static commentBlockModel = RegionCommentBlock;
}
