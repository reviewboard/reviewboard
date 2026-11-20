/**
 * Represents the comments on a region of a diff.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import { type DiffComment } from 'reviewboard/common';

import {
    type AbstractCommentBlockAttrs,
    AbstractCommentBlock,
} from './abstractCommentBlockModel';
import {
    type SerializedViewModeData,
    VIEW_MODE_COMMENT_FIELDS,
} from './commentData';


/**
 * Attributes for the DiffCommentBlock model.
 *
 * Version Changed:
 *     9.0:
 *     Added ``viewMode`` and ``renderVersion`` from
 *     :js:class:`SerializedViewModeData`.
 *
 * Version Added:
 *     7.0
 */
export interface DiffCommentBlockAttrs
    extends AbstractCommentBlockAttrs, SerializedViewModeData {
    /** The first row in the diffviewer that this comment is on. */
    $beginRow: JQuery;

    /** The last row in the diffviewer that this comment is on. */
    $endRow: JQuery;

    /**
     * The ID of the base FileDiff that this comment is on.
     *
     * This attribute is mutually exclusive with interFileDiffID.
     */
    baseFileDiffID: number;

    /** The first line number in the file that this comment is on. */
    beginLineNum: number;

    /** The last line number in the file that this comment is on. */
    endLineNum: number;

    /** The ID of the FileDiff that this comment is on. */
    fileDiffID: number;

    /**
     * The ID of the inter-FileDiff that this comment is on, if any.
     *
     * This attribute is mutually exclusive with baseFileDiffID.
     */
    interFileDiffID: number;

    /** Whether the diff for this comment has been published. */
    public: boolean;
}


/**
 * Represents the comments on a region of a diff.
 *
 * DiffCommentBlock deals with creating and representing comments that exist
 * in a specific line range of a diff.
 *
 * See Also:
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For the attributes defined by the base model.
 */
@spina
export class DiffCommentBlock
    extends AbstractCommentBlock<DiffCommentBlockAttrs> {
    /** Default values for the model attributes. */
    static defaults: Result<Partial<DiffCommentBlockAttrs>> = {
        $beginRow: null,
        $endRow: null,
        baseFileDiffID: null,
        beginLineNum: null,
        endLineNum: null,
        fileDiffID: null,
        interFileDiffID: null,
        public: false,
        viewMode: 'source',
    };

    static serializedFields = [
        'line',
        'num_lines',
        ...VIEW_MODE_COMMENT_FIELDS,
    ];

    /**
     * Return the number of lines this comment block spans.
     *
     * Returns:
     *     number:
     *     The number of lines spanned by this comment.
     */
    getNumLines(): number {
        return this.get('endLineNum') + this.get('beginLineNum') + 1;
    }

    /**
     * Create a DiffComment for the given comment ID.
     *
     * Args:
     *     id (number):
     *         The ID of the comment to instantiate the model for.
     *
     * Returns:
     *     RB.DiffComment:
     *     The new comment model.
     */
    createComment(
        id: number,
    ): DiffComment {
        const comment = this.get('review').createDiffComment({
            baseFileDiffID: this.get('baseFileDiffID'),
            beginLineNum: this.get('beginLineNum'),
            endLineNum: this.get('endLineNum'),
            fileDiffID: this.get('fileDiffID'),
            id: id,
            interFileDiffID: this.get('interFileDiffID'),
        });

        /* Only files with a rendered view need to store the view mode. */
        if (this.get('renderVersion')) {
            _.extend(comment.get('extraData'),
                     _.pick(this.attributes, VIEW_MODE_COMMENT_FIELDS));
        }

        return comment;
    }

    /**
     * Return a warning about commenting on a draft object.
     *
     * Returns:
     *     string:
     *     A warning to display to the user if they're commenting on a draft
     *     object. Return null if there's no warning.
     */
    getDraftWarning(): string {
        if (this.get('public')) {
            return null;
        } else {
            return _`
                The diff for this comment is still a draft. Replacing the
                draft diff will delete this comment.
            `;
        }
    }
}
