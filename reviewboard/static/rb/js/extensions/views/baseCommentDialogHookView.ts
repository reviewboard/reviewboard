/**
 * Base support for custom comment dialog hook views.
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

import {
    type CommentDialogView,
    type CommentEditor,
} from 'reviewboard/reviews';

import {
    type Extension,
} from '../models/extensionModel';


/**
 * Options for BaseCommentDialogHookView.
 *
 * Version Added:
 *     7.1
 */
export interface CommentDialogHookViewOptions extends Backbone.ViewOptions {
    /** The comment dialog being rendered into. */
    commentDialog: CommentDialogView;

    /** The comment editor managing comments in the dialog. */
    commentEditor: CommentEditor;

    /** The extension that owns the hook. */
    extension: Extension;
}


/**
 * A base view for rendering into a comment dialog.
 *
 * This is intended to be subclassed and passed in a view type to
 * :js:class:`RB.CommentDialogViewHook`. It takes in the comment dialog,
 * editor, and parent extension, and can then render into the dialog or
 * hook into behavior.
 *
 * Version Added:
 *     7.1
 */
@spina
export class BaseCommentDialogHookView extends BaseView<
    BaseModel,
    HTMLDivElement,
    unknown,
    CommentDialogHookViewOptions
> {
    /**********************
     * Instance variables *
     **********************/

    /** The comment dialog being rendered into. */
    commentDialog: CommentDialogView;

    /** The comment editor managing comments in the dialog. */
    commentEditor: CommentEditor;

    /** The extension that owns the hook. */
    extension: Extension;

    /**
     * Pre-initialize the view.
     *
     * This will set the instance attributes based on the options provided
     * before the subclass's initialization code runs.
     *
     * Args:
     *     options (CommentDialogHookViewOptions):
     *         The options for the view.
     */
    preinitialize(
        options: Partial<CommentDialogHookViewOptions>,
    ) {
        this.commentDialog = options.commentDialog;
        this.commentEditor = options.commentEditor;
        this.extension = options.extension;
    }
}


/**
 * A type representing a BaseCommentDialogHookView class.
 *
 * This types the constructor of the class such that it will properly return
 * an instance that is typed with the right constructor arguments and default
 * generics.
 *
 * Version Added:
 *     7.1
 */
export type BaseCommentDialogHookViewClass =
    new (options: CommentDialogHookViewOptions) => BaseCommentDialogHookView;
