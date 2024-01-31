/**
 * Base support for displaying a review UI for file attachments.
 */

import { spina } from '@beanbag/spina';

import {
    FileAttachmentReviewable,
} from '../models/fileAttachmentReviewableModel';
import {
    AbstractReviewableView,
    AbstractReviewableViewOptions,
} from './abstractReviewableView';


/**
 * Base support for displaying a review UI for file attachments.
 */
@spina
export class FileAttachmentReviewableView<
    TModel extends FileAttachmentReviewable = FileAttachmentReviewable,
    TElement extends Element = HTMLElement,
    TExtraViewOptions extends AbstractReviewableViewOptions =
        AbstractReviewableViewOptions
> extends AbstractReviewableView<TModel, TElement, TExtraViewOptions> {
    static commentsListName = 'file_attachment_comments';
}
