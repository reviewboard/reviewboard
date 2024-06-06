/**
 * Provides generic review capabilities for file attachments.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import { type AbstractCommentBlock } from './abstractCommentBlockModel';
import {
    type AbstractReviewableAttrs,
    AbstractReviewable,
} from './abstractReviewableModel';
import { type SerializedComment } from './commentData';


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
    static defaults: Result<Partial<FileAttachmentReviewableAttrs>> = {
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
    };

    static defaultCommentBlockFields = [
        'fileAttachmentID',
        'diffAgainstFileAttachmentID',
        'state',
    ];

    /**
     * Load a serialized comment and add comment blocks for it.
     *
     * Args:
     *     serializedComments (Array of SerializedComment):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(
        serializedComments: SerializedComment[],
    ) {
        const parsedData = this.commentBlockModel.prototype.parse(
            _.pick(serializedComments[0],
                   this.commentBlockModel.prototype.serializedFields));

        this.createCommentBlock(_.extend(
            {
                diffAgainstFileAttachmentID:
                    this.get('diffAgainstFileAttachmentID'),
                fileAttachmentID: this.get('fileAttachmentID'),
                serializedComments: serializedComments,
                state: this.get('state'),
            }, parsedData));
    }
}
