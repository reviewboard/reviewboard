/**
 * A reply to a file attachment comment made on a review.
 */

import { spina } from '@beanbag/spina';

import { BaseCommentReply } from './baseCommentReplyModel';


/**
 * A reply to a file attachment comment made on a review.
 *
 * When created, this must take a parentObject attribute that points to a
 * Review object.
 */
@spina
export class FileAttachmentCommentReply extends BaseCommentReply {
    static rspNamespace = 'file_attachment_comment';
}
