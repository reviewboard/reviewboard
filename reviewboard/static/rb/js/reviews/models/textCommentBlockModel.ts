/**
 * Represents the comments on an element in a text-based file attachment.
 */

import { spina } from '@beanbag/spina';

import {
    type FileAttachmentCommentBlockAttrs,
    FileAttachmentCommentBlock,
} from './fileAttachmentCommentBlockModel';


/**
 * Attributes for the TextCommentBlock model.
 *
 * Version Added:
 *     6.0
 */
export interface TextCommentBlockAttrs
    extends FileAttachmentCommentBlockAttrs {
    /** The first row in the diffviewer that this comment is on. */
    $beginRow: JQuery;

    /** The last row in the diffviewer that this comment is on. */
    $endRow: JQuery;

    /** The first line number in the file that this comment is on. */
    beginLineNum: number;

    /** The last line number in the file that this comment is on. */
    endLineNum: number;

    /**
     * The mode of text that the comment is made upon. This is one of:
     *
     * ``'source'``:
     *     The raw contents of the file.
     *
     * ``'rendered'``:
     *     The rendered contents of the file, such as for Markdown, etc.
     */
    viewMode: string;
}


/**
 * The serialized comment data.
 *
 * Version Added:
 *     7.0
 */
interface SerializedTextCommentFields {
    beginLineNum: string;
    endLineNum: string;
}


/**
 * Represents the comments on an element in a text-based file attachment.
 *
 * TextCommentBlock deals with creating and representing comments
 * that exist on a specific element of some content.
 *
 * See Also:
 *     :js:class:`RB.FileAttachmentCommentBlock`:
 *         For the attributes defined by the base model.
 *
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For the attributes defined on all comment block.
 */
@spina
export class TextCommentBlock<
    TAttributes extends TextCommentBlockAttrs = TextCommentBlockAttrs
> extends FileAttachmentCommentBlock<TAttributes> {
    static defaults: TextCommentBlockAttrs = _.defaults({
        $beginRow: null,
        $endRow: null,
        beginLineNum: null,
        endLineNum: null,
        viewMode: false,
    }, super.defaults);

    static serializedFields = ['beginLineNum', 'endLineNum', 'viewMode'];

    /**
     * Parse the incoming attributes for the comment block.
     *
     * The fields are stored server-side as strings, so we need to convert
     * them back to integers where appropriate.
     *
     * Args:
     *     fields (object):
     *         The attributes for the comment, as returned by the server.
     *
     * Returns:
     *     object:
     *     The parsed data.
     */
    parse(
        fields: SerializedTextCommentFields,
    ): Partial<TextCommentBlockAttrs> {
        return {
            beginLineNum: parseInt(fields.beginLineNum, 10),
            endLineNum: parseInt(fields.endLineNum, 10),
        };
    }
}
