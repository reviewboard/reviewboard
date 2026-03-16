/**
 * Provides general commenting functionality for review requests.
 */

import { spina } from '@beanbag/spina';

import { BaseComment } from './baseCommentModel';


/**
 * Model for a general comment on a review request.
 *
 * Examples include suggestions for testing or pointing out errors in
 * the change description. An issue can be opened.
 */
@spina
export class GeneralComment extends BaseComment {
    static rspNamespace = 'general_comment';
}
