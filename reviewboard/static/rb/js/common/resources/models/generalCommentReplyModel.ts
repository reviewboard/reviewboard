/**
 * A reply to a general comment made on a review.
 */

import { spina } from '@beanbag/spina';

import { BaseCommentReply } from './baseCommentReplyModel';


/**
 * A reply to a general comment made on a review.
 *
 * When created, this must take a parentObject attribute that points to a
 * Review object.
 */
@spina
export class GeneralCommentReply extends BaseCommentReply {
    static rspNamespace = 'general_comment';
}
