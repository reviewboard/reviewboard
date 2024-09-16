/** The file attachment resource model. */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import { onlyIfNew } from '../utils/serializers';
import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    type SerializerMap,
    BaseResource,
} from './baseResourceModel';


/**
 * States for file attachments.
 *
 * This coincides with
 * :py:class:`reviewboard.reviews.models.review_request.FileAttachmentState`.
 *
 * Version Added:
 *     6.0
 */
export enum FileAttachmentStates {
    /** A published file attachment that has been deleted. */
    DELETED = 'deleted',

    /**
     * A draft version of a file attachment that has been published before.
     *
     * These are file attachments that have a draft update to their caption.
     */
    DRAFT = 'draft',

    /** A new draft file attachment that has never been published before. */
    NEW = 'new',

    /** A draft file attachment that is a new revision of an existing one. */
    NEW_REVISION = 'new-revision',

    /**
     * A file attachment that is pending deletion.
     *
     * These are previously published file attachments that have been deleted
     * from a review request draft, but have not been fully deleted yet because
     * the review request draft has not been published.
     */
    PENDING_DELETION = 'pending-deletion',

    /** A published file attachment. */
    PUBLISHED = 'published',
}


/**
 * Attributes for the FileAttachment model.
 *
 *
 * Version Changed:
 *     7.0.3:
 *     Added the ``canAccessReviewUI`` attribute.
 *
 * Version Added:
 *     6.0
 */
export interface FileAttachmentAttrs extends BaseResourceAttrs {
    /** The ID of the file attachment's history. */
    attachmentHistoryID: number;

    /**
     * The file attachment's caption.
     *
     *  This may be a draft caption.
     */
    caption: string;

    /** The URL to download an existing file attachment. */
    downloadURL: string;

    /** The file to upload. Only works for newly created FileAttachments. */
    file: File;

    /** The name of the file, for existing file attachments. */
    filename: string;

    /**
     * Whether the current user can access the file attachment's review UI.
     *
     * Version Added:
     *     7.0.3
     */
    canAccessReviewUI: string;

    /** The file attachment's latest published caption. */
    publishedCaption: string;

    /** The URL to the review UI for this file attachment. */
    reviewURL: string;

    /** The revision of the file attachment. */
    revision: number;

    /** The state of the file attachment. */
    state: string;

    /** The HTML for the thumbnail depicting this file attachment. */
    thumbnailHTML: string;
}


/**
 * Resource data for the FileAttachment model.
 *
 * Version Added:
 *     7.0
 */
export interface FileAttachmentResourceData extends BaseResourceResourceData {
    attachment_history_id: number;
    is_review_ui_accessible_by: string;
    caption: string;
    filename: string;
    review_url: string;
    revision: string;
    state: string;
    thumbnail: string;
    url: string;
}


/**
 * Represents a new or existing file attachment.
 */
@spina
export class FileAttachment extends BaseResource<
    FileAttachmentAttrs,
    FileAttachmentResourceData
> {
    /**
     * Return default values for the model attributes.
     *
     * Returns:
     *     object:
     *     The attribute defaults.
     */
    static defaults: Result<Partial<FileAttachmentAttrs>> = {
        'attachmentHistoryID': null,
        'canAccessReviewUI': null,
        'caption': null,
        'downloadURL': null,
        'file': null,
        'filename': null,
        'publishedCaption': null,
        'reviewURL': null,
        'revision': null,
        'state': FileAttachmentStates.NEW,
        'thumbnailHTML': null,
    };

    static rspNamespace = 'file_attachment';
    static payloadFileKeys = ['path'];
    static supportsExtraData = true;

    static attrToJsonMap: { [key: string]: string } = {
        attachmentHistoryID: 'attachment_history_id',
        canAccessReviewUI: 'is_review_ui_accessible_by',
        downloadURL: 'url',
        file: 'path',
        reviewURL: 'review_url',
        thumbnailHTML: 'thumbnail',
    };

    static serializedAttrs = [
        'attachmentHistoryID',
        'caption',
        'file',
    ];

    static deserializedAttrs = [
        'attachmentHistoryID',
        'canAccessReviewUI',
        'caption',
        'downloadURL',
        'filename',
        'reviewURL',
        'revision',
        'state',
        'thumbnailHTML',
    ];

    static serializers: SerializerMap = {
        'attachmentHistoryID': onlyIfNew,
        'file': onlyIfNew,
    };
}
