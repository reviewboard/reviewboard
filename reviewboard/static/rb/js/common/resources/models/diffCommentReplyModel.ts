/**
 * A reply to a diff comment made on a review.
 */

import { spina } from '@beanbag/spina';

import {
    BaseCommentReply,
} from './baseCommentReplyModel';


/**
 * A reply to a diff comment made on a review.
 *
 * When created, this must take a parentObject attribute that points to a
 * Review object.
 */
@spina
export class DiffCommentReply extends BaseCommentReply {
    static rspNamespace = 'diff_comment';
}
