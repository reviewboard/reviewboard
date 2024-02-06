/**
 * Provides generic review capabilities for file attachments.
 */

import { spina } from '@beanbag/spina';

import {
    AbstractCommentBlock,
    SerializedComment,
} from './abstractCommentBlockModel';
import {
    AbstractReviewable,
    AbstractReviewableAttrs,
} from './abstractReviewableModel';


/**
 * Attributes for the FileAttachmentReviewable model.
 *
 * Version Added:
 *     7.0
 */
export interface FileAttachmentReviewableAttrs
    extends AbstractReviewableAttrs {
    /** The revisions of the file attachment. */
    attachmentRevisionIDs: number[];

    /** The ID of the file attachment being diffed against. */
    diffAgainstFileAttachmentID: number;

    /** The caption of the attachment being diffed against. */
    diffCaption: string;

    /** The revision of the attachment being diffed against. */
    diffRevision: number;

    /** Whether the attachments being diffed have different review UI types. */
    diffTypeMismatch: boolean;

    /** The ID of the file attachment being reviewed. */
    fileAttachmentID: number;

    /** The revision of the file attachment being reviewed. */
    fileRevision: number;

    /** The name of the file being reviewed. */
    filename: string;

    /** The total number of revisions for the given attachment. */
    numRevisions: number;

    /** The state of the file attachment. */
    state: string;
}


/**
 * Provides generic review capabilities for file attachments.
 *
 * See Also:
 *     :js:class:`RB.AbstractReviewable`:
 *         For attributes defined on the base model.
 */
@spina
export class FileAttachmentReviewable<
    TAttributes extends FileAttachmentReviewableAttrs =
        FileAttachmentReviewableAttrs,
    TCommentBlockType extends AbstractCommentBlock = null
> extends AbstractReviewable<TAttributes, TCommentBlockType> {
    static defaults: FileAttachmentReviewableAttrs = _.defaults({
        attachmentRevisionIDs: null,
        diffAgainstFileAttachmentID: null,
        diffCaption: '',
        diffRevision: null,
        diffTypeMismatch: false,
        fileAttachmentID: null,
        fileRevision: null,
        filename: '',
        numRevisions: null,
        state: null,
    }, super.defaults);

    static defaultCommentBlockFields = [
        'fileAttachmentID',
        'diffAgainstFileAttachmentID',
        'state',
    ];

    /**
     * Load a serialized comment and add comment blocks for it.
     *
     * Args:
     *     serializedCommentBlock (object):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(
        serializedCommentBlock: SerializedComment[],
    ) {
        const parsedData = this.commentBlockModel.prototype.parse(
            _.pick(serializedCommentBlock[0],
                   this.commentBlockModel.prototype.serializedFields));

        this.createCommentBlock(_.extend(
            {
                diffAgainstFileAttachmentID:
                    this.get('diffAgainstFileAttachmentID'),
                fileAttachmentID: this.get('fileAttachmentID'),
                serializedComments: serializedCommentBlock,
                state: this.get('state'),
            }, parsedData));
    }
}
