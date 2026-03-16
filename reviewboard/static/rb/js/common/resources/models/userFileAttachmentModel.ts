/**
 * A new or existing user file attachment.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import { UserSession } from '../../models/userSessionModel';
import * as JSONSerializers from '../utils/serializers';
import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    type SerializerMap,
    BaseResource,
} from './baseResourceModel';


/**
 * Attributes for the UserFileAttachment model.
 *
 * Version Added:
 *     8.0
 */
export interface UserFileAttachmentAttrs extends BaseResourceAttrs {
    /** The file attachment's caption. */
    caption: string;

    /** The URL to download the file, for existing file attachments. */
    downloadURL: string;

    /**
     * The file to upload.
     *
     * This is only used for newly created UserFileAttachments.
     */
    file: File | string;

    /** The name of the file, for existing file attachments. */
    filename: string;
}


/**
 * Resource data for the UserFileAttachment model.
 *
 * Version Added:
 *     8.0
 */
export interface UserFileAttachmentResourceData
extends BaseResourceResourceData {
    absolute_url: string;
    caption: string;
    path: string;
}


/**
 * A new or existing user file attachment.
 */
@spina
export class UserFileAttachment extends BaseResource<
    UserFileAttachmentAttrs,
    UserFileAttachmentResourceData
> {
    static defaults: Result<Partial<UserFileAttachmentAttrs>> = {
        caption: null,
        downloadURL: null,
        file: null,
        filename: null,
    };

    static rspNamespace = 'user_file_attachment';
    static payloadFileKeys = ['path'];

    static attrToJsonMap: Record<string, string> = {
        downloadURL: 'absolute_url',
        file: 'path',
    };

    static serializedAttrs = [
        'caption',
        'file',
    ];

    static deserializedAttrs = [
        'caption',
        'downloadURL',
        'filename',
    ];

    static serializers: SerializerMap = {
        file: JSONSerializers.onlyIfValue,
    };

    /**
     * Return the URL to use for syncing the model.
     *
     * Returns:
     *     string:
     *     The URL for the resource.
     */
    url(): string {
        const url = UserSession.instance.get('userFileAttachmentsURL');

        return this.isNew() ? url : `${url}${this.id}/`;
    }
}
