/**
 * Provides generic review capabilities for text-based file attachments.
 */

import { spina } from '@beanbag/spina';

import {
    FileAttachmentReviewable,
    FileAttachmentReviewableAttrs,
} from './fileAttachmentReviewableModel';
import { TextCommentBlock } from './textCommentBlockModel';


/**
 * Attributes for the TextBasedReviewable model.
 *
 * Version Added:
 *     7.0
 */
export interface TextBasedReviewableAttrs
    extends FileAttachmentReviewableAttrs {
    /** Whether the text has a rendered view, such as for Markdown. */
    hasRenderedView: boolean;

    /**
     * The mode of text currently being displayed. This is one of:
     *
     * ``'source'``:
     *     The raw contents of the file.
     *
     * ``'rendered'``:
     *     The rendered contents of the file, such as for Markdown.
     */
    viewMode: string;
}


/**
 * Provides generic review capabilities for text-based file attachments.
 */
@spina
export class TextBasedReviewable<
    TAttributes extends TextBasedReviewableAttrs = TextBasedReviewableAttrs,
    TCommentBlockType extends TextCommentBlock = TextCommentBlock
> extends FileAttachmentReviewable<TAttributes, TCommentBlockType> {
    static defaults: FileAttachmentReviewableAttrs = _.defaults({
        hasRenderedView: false,
        viewMode: 'source',
    }, super.defaults);

    static commentBlockModel = TextCommentBlock;

    static defaultCommentBlockFields = [
        'viewMode',
    ].concat(super.defaultCommentBlockFields);
}
