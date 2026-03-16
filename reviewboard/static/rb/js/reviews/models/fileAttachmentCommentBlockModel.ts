/**
 * Represents the comments on a file attachment.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    type FileAttachmentComment,
    FileAttachmentStates,
} from 'reviewboard/common';
import {
    type AbstractCommentBlockAttrs,
    AbstractCommentBlock,
} from './abstractCommentBlockModel';


/**
 * Attributes for the FileAttachmentCommentBlock model.
 *
 * Version Added:
 *     7.0
 */
export interface FileAttachmentCommentBlockAttrs
extends AbstractCommentBlockAttrs {
    /** An optional ID of the file attachment being diffed against. */
    diffAgainstFileAttachmentID: number;

    /** The ID of the file attachment being commented upon. */
    fileAttachmentID: number;

    /** The state of the file attachment. */
    state: string;
}


/**
 * Represents the comments on a file attachment.
 *
 * FileAttachmentCommentBlock deals with creating and representing comments
 * that exist on a file attachment. It's a base class that is meant to be
 * subclassed.
 *
 * See Also:
 *     :js:class:`RB.AbstractCommentBlock`:
 *         For attributes defined on the base model.
 */
@spina
export class FileAttachmentCommentBlock<
    TAttributes extends FileAttachmentCommentBlockAttrs
> extends AbstractCommentBlock<TAttributes> {
    /** Default values for the model attributes. */
    static defaults: Result<Partial<FileAttachmentCommentBlockAttrs>> = {
        diffAgainstFileAttachmentID: null,
        fileAttachmentID: null,
        state: null,
    };

    /**
     * Create a FileAttachmentComment for the given comment ID.
     *
     * The subclass's storeCommentData will be called, allowing additional
     * data to be stored along with the comment.
     *
     * Args:
     *     id (number):
     *         The ID of the comment to instantiate the model for.
     *
     * Returns:
     *     RB.FileAttachmentComment:
     *     The new comment model.
     */
    createComment(
        id: number,
    ): FileAttachmentComment {
        const comment = this.get('review').createFileAttachmentComment(
            id,
            this.get('fileAttachmentID'),
            this.get('diffAgainstFileAttachmentID'));

        _.extend(comment.get('extraData'),
                 _.pick(this.attributes, this.serializedFields));

        return comment;
    }

    /**
     * Return a warning about commenting on a deleted object.
     *
     * Version Added:
     *     6.0
     *
     * Returns:
     *     string:
     *     A warning to display to the user if they're commenting on a deleted
     *     object. Return null if there's no warning.
     */
    getDeletedWarning(): string {
        if (this.get('state') === FileAttachmentStates.DELETED) {
            return _`This file is deleted and cannot be commented on.`;
        } else {
            return null;
        }
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
        const state = this.get('state');

        if (state === FileAttachmentStates.NEW ||
            state === FileAttachmentStates.NEW_REVISION ||
            state === FileAttachmentStates.DRAFT) {
            return _`The file for this comment is still a draft. Replacing or
                     deleting the file will delete this comment.`;
        } else {
            return null;
        }
    }
}
