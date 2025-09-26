/**
 * Base support for custom Review Dialog comment hook views.
 *
 * Version Added:
 *     7.1
 */

import * as Backbone from 'backbone';
import {
    type BaseModel,
    BaseView,
    spina,
} from '@beanbag/spina';

import { type Extension } from '../models/extensionModel';


/**
 * Options for BaseReviewDialogCommentHookView.
 *
 * Version Added:
 *     7.1
 */
export interface ReviewDialogCommentHookViewOptions
extends Backbone.ViewOptions {
    /** The extension that owns the hook. */
    extension: Extension;
}


/**
 * A base view for rendering into comment sections in the Review Dialog.
 *
 * This is intended to be subclassed and passed in a view type to
 * :js:class:`RB.ReviewDialogCommentViewHook`. It takes in the parent
 * extension and can then render into the dialog or hook into behavior.
 *
 * Version Added:
 *     7.1
 */
@spina
export class BaseReviewDialogCommentHookView extends BaseView<
    BaseModel,
    HTMLDivElement,
    unknown,
    ReviewDialogCommentHookViewOptions
> {
    /**********************
     * Instance variables *
     **********************/

    /** The extension that owns the hook. */
    extension: Extension;

    /**
     * Pre-initialize the view.
     *
     * This will set the instance attributes based on the options provided
     * before the subclass's initialization code runs.
     *
     * Args:
     *     options (ReviewDialogCommentHookViewOptions):
     *         The options for the view.
     */
    preinitialize(
        options: Partial<ReviewDialogCommentHookViewOptions>,
    ) {
        this.extension = options.extension;
    }
}


/**
 * A type representing a BaseReviewDialogCommentHookView class.
 *
 * This types the constructor of the class such that it will properly return
 * an instance that is typed with the right constructor arguments and default
 * generics.
 *
 * Version Added:
 *     7.1
 */
export type BaseReviewDialogCommentHookViewClass =
    new (options: ReviewDialogCommentHookViewOptions) =>
    BaseReviewDialogCommentHookView;
