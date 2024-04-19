/**
 * Displays the comment flag for a comment in the diff viewer.
 */

import { spina } from '@beanbag/spina';

import { type DiffCommentBlock } from '../models/diffCommentBlockModel';
import { TextBasedCommentBlockView } from './textBasedCommentBlockView';


/**
 * Displays the comment flag for a comment in the diff viewer.
 *
 * The comment flag handles all interaction for creating/viewing
 * comments, and will update according to any comment state changes.
 */
@spina
export class DiffCommentBlockView extends TextBasedCommentBlockView<
    DiffCommentBlock
> {
    /**
     * Return the name for the comment flag anchor.
     *
     * Returns:
     *     string:
     *     The name to use for the anchor element.
     */
    buildAnchorName(): string {
        const fileDiffID = this.model.get('fileDiffID');
        const beginLineNum = this.model.get('beginLineNum');

        return `file${fileDiffID}line${beginLineNum}`;
    }
}
