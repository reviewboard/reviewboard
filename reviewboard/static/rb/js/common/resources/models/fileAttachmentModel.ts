/** The file attachment resource model. */

import { spina } from '@beanbag/spina';

import { onlyIfNew } from '../utils/serializers';
import { BaseResource, BaseResourceAttrs } from './baseResourceModel';


/**
 * Attributes for the FileAttachment model.
 *
 * Version Added:
 *     6.0
 */
export interface FileAttachmentAttrs extends BaseResourceAttrs {
    /** The ID of the file attachment's history. */
    attachmentHistoryID: number;

    /** The file attachment's caption. */
    caption: string;

    /** The URL to download an existing file attachment. */
    downloadURL: string;

    /** The file to upload. Only works for newly created FileAttachments. */
    file: File;

    /** The name of the file, for existing file attachments. */
    filename: string;

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
 * Represents a new or existing file attachment.
 */
@spina({
    prototypeAttrs: [
        'attrToJsonMap',
        'deserializedAttrs',
        'payloadFileKeys',
        'rspNamespace',
        'serializedAttrs',
        'serializers',
        'supportsExtraData',
    ],
})
export class FileAttachment extends BaseResource<FileAttachmentAttrs> {
    /**
     * Return default values for the model attributes.
     *
     * Returns:
     *     object:
     *     The attribute defaults.
     */
    defaults(): FileAttachmentAttrs {
        return _.defaults({
            'attachmentHistoryID': null,
            'caption': null,
            'downloadURL': null,
            'file': null,
            'filename': null,
            'reviewURL': null,
            'revision': null,
            'state': 'New',
            'thumbnailHTML': null,
        }, super.defaults());
    }

    static rspNamespace = 'file_attachment';
    static payloadFileKeys = ['path'];
    static supportsExtraData = true;

    static attrToJsonMap = {
        attachmentHistoryID: 'attachment_history_id',
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
        'caption',
        'downloadURL',
        'filename',
        'reviewURL',
        'revision',
        'state',
        'thumbnailHTML',
    ];

    static serializers = {
        'attachmentHistoryID': onlyIfNew,
        'file': onlyIfNew,
    };
}
