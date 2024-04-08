/**
 * Generic review capabilities for file types which cannot be displayed.
 */

import { spina } from '@beanbag/spina';

import { AbstractCommentBlock } from './abstractCommentBlockModel';
import {
    type FileAttachmentReviewableAttrs,
    FileAttachmentReviewable,
} from './fileAttachmentReviewableModel';


/**
 * Generic review capabilities for file types which cannot be displayed.
 */
@spina
export class DummyReviewable extends FileAttachmentReviewable<
    FileAttachmentReviewableAttrs,
    AbstractCommentBlock
> {
    static commentBlockModel = AbstractCommentBlock;
}
