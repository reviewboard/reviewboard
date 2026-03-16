/**
 * A comment on a file attachment.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import * as JSONSerializers from '../utils/serializers';
import {
    type BaseCommentAttrs,
    type BaseCommentResourceData,
    BaseComment,
} from './baseCommentModel';
import {
    type SerializerMap,
} from './baseResourceModel';
import {
    type FileAttachmentResourceData,
    FileAttachment,
} from './fileAttachmentModel';


/**
 * Attributes for the FileAttachmentComment model.
 *
 * Version Added:
 *     8.0
 */
export interface FileAttachmentCommentAttrs extends BaseCommentAttrs {
    /**
     * The file attachment that is the "new" side of a comment.
     */
    diffAgainstFileAttachment: FileAttachment;

    /**
     * The ID of the file attachment that is the "new" side of a comment.
     */
    diffAgainstFileAttachmentID: number;

    /**
     * The file attachment that the comment is on.
     *
     * If the comment is on a single revision of the file, this will be that
     * file attachment object. If the comment is on a diff, this is the
     * attachment that is the "old" side of the diff.
     */
    fileAttachment: FileAttachment;

    /**
     * The ID of the file attachment that the comment is on.
     *
     * If the comment is on a single revision of the file, this will be the ID
     * of that file attachment. If the comment is on a diff, this is the ID of
     * the attachment that is the "old" side of the diff.
     */
    fileAttachmentID: number;

    /**
     * The text used to describe a link to the file.
     *
     * This may differ depending on the comment.
     */
    linkText: string;

    /** The URL for the file attachment review UI for the comment. */
    reviewURL: string;

    /** The HTML representing a thumbnail, if any, for this comment. */
    thumbnailHTML: string;
}


/**
 * Resource data for the FileAttachmentComment.
 *
 * Version Added:
 *     8.0
 */
export interface FileAttachmentCommentResourceData
extends BaseCommentResourceData {
    diff_against_file_attachment?: FileAttachmentResourceData;
    diff_against_file_attachment_id?: number;
    file_attachment: FileAttachmentResourceData;
    file_attachment_id: number;
    link_text: string;
    review_url: string;
    thumbnail_html: string;
}


/**
 * A comment on a file attachment.
 */
@spina
export class FileAttachmentComment extends BaseComment<
    FileAttachmentCommentAttrs,
    FileAttachmentCommentResourceData
> {
    static defaults: Result<Partial<FileAttachmentCommentAttrs>> = {
        diffAgainstFileAttachment: null,
        diffAgainstFileAttachmentID: null,
        fileAttachment: null,
        fileAttachmentID: null,
        linkText: null,
        reviewURL: null,
        thumbnailHTML: null,
    };

    static rspNamespace = 'file_attachment_comment';
    static expandedFields = [
        'diff_against_file_attachment',
        'file_attachment',
    ];

    static attrToJsonMap: Record<string, string> = {
        diffAgainstFileAttachmentID: 'diff_against_file_attachment_id',
        fileAttachmentID: 'file_attachment_id',
        linkText: 'link_text',
        reviewURL: 'review_url',
        thumbnailHTML: 'thumbnail_html',
    };

    static serializedAttrs = [
        'diffAgainstFileAttachmentID',
        'fileAttachmentID',
    ].concat(super.serializedAttrs);

    static deserializedAttrs = [
        'linkText',
        'thumbnailHTML',
        'reviewURL',
    ].concat(super.deserializedAttrs);

    static serializers: SerializerMap = {
        diffAgainstFileAttachmentID: JSONSerializers.onlyIfUnloadedAndValue,
        fileAttachmentID: JSONSerializers.onlyIfUnloaded,
    };

    static strings = {
        INVALID_FILE_ATTACHMENT_ID: 'fileAttachmentID must be a valid ID',
    };

    /**
     * Deserialize comment data from an API payload.
     *
     * Args:
     *     rsp (FileAttachmentCommentResourceData):
     *         The response from the server.
     *
     * Returns:
     *     FileAttachmentCommentAttrs:
     *     Attribute values to set on the model.
     */
    parseResourceData(
        rsp: FileAttachmentCommentResourceData,
    ): Partial<FileAttachmentCommentAttrs> {
        const result = super.parseResourceData(rsp);

        result.fileAttachment = new FileAttachment(rsp.file_attachment, {
            parse: true,
        });
        result.fileAttachmentID = result.fileAttachment.id as number;

        if (rsp.diff_against_file_attachment) {
            result.diffAgainstFileAttachment = new FileAttachment(
                rsp.diff_against_file_attachment, {
                    parse: true,
                });

            result.diffAgainstFileAttachmentID =
                result.diffAgainstFileAttachment.id as number;
        }

        return result;
    }

    /**
     * Perform validation on the attributes of the model.
     *
     * This will check the file attachment ID along with the default
     * comment validation.
     *
     * Args:
     *     attrs (object):
     *         Model attributes to validate.
     *
     * Returns:
     *     string:
     *     An error string, if appropriate.
     */
    validate(
        attrs: Partial<FileAttachmentCommentAttrs>,
    ): string {
        if (_.has(attrs, 'fileAttachmentID') && !attrs.fileAttachmentID) {
            return FileAttachmentComment.strings.INVALID_FILE_ATTACHMENT_ID;
        }

        return super.validate(attrs);
    }
}
