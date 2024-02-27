/**
 * Displays a review UI for Markdown files.
 */

import { spina } from '@beanbag/spina';

import { TextBasedReviewableView } from './textBasedReviewableView';


/**
 * Displays a review UI for Markdown files.
 */
@spina
export class MarkdownReviewableView extends TextBasedReviewableView {
    static className = 'markdown-review-ui';
}
