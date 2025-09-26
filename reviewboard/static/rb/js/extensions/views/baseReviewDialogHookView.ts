/**
 * Base support for custom Review Dialog hook views.
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
 * Options for BaseReviewDialogHookView.
 *
 * Version Added:
 *     7.1
 */
export interface ReviewDialogHookViewOptions extends Backbone.ViewOptions {
    /** The extension that owns the hook. */
    extension: Extension;
}


/**
 * A base view for rendering into the Review Dialog.
 *
 * This is intended to be subclassed and passed in a view type to
 * :js:class:`RB.ReviewDialogViewHook`. It takes in the parent extension
 * and can then render into the dialog or hook into behavior.
 *
 * Version Added:
 *     7.1
 */
@spina
export class BaseReviewDialogHookView extends BaseView<
    BaseModel,
    HTMLDivElement,
    unknown,
    ReviewDialogHookViewOptions
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
     *     options (ReviewDialogHookViewOptions):
     *         The options for the view.
     */
    preinitialize(
        options: Partial<ReviewDialogHookViewOptions>,
    ) {
        this.extension = options.extension;
    }
}


/**
 * A type representing a BaseReviewDialogHookView class.
 *
 * This types the constructor of the class such that it will properly return
 * an instance that is typed with the right constructor arguments and default
 * generics.
 *
 * Version Added:
 *     7.1
 */
export type BaseReviewDialogHookViewClass =
    new (options: ReviewDialogHookViewOptions) => BaseReviewDialogHookView;
