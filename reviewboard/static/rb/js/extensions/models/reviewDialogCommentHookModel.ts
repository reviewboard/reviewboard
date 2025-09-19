/**
 * Extension hook for extending a comment in the Review Dialog.
 *
 * Version Changed:
 *     7.1:
 *     This is now an ESM module supporting TypeScript.
 */

import { spina } from '@beanbag/spina';

import {
    type ExtensionHookAttrs,
    ExtensionHook,
} from './extensionHookModel';
import { ExtensionHookPoint } from './extensionHookPointModel';
import {
    type BaseReviewDialogCommentHookViewClass,
} from '../views/baseReviewDialogCommentHookView';


/**
 * Attributes for ReviewDialogCommentHook.
 *
 * Version Added:
 *     7.1
 */
export interface ReviewDialogCommentHookAttrs extends ExtensionHookAttrs {
    /** The view type to construct in the comment section. */
    viewType: BaseReviewDialogCommentHookViewClass;
}


/**
 * Adds additional rendering or UI for a comment in the review dialog.
 *
 * This can be used to display additional UI and even additional fields in
 * the review dialog, which can reflect and potentially modify extra data
 * for a comment.
 *
 * A View type (not an instance) must be provided for the viewType
 * attribute. When rendering comments in the dialog, an instance of the
 * provided view will be created and passed the comment as the view's model.
 *
 * Version Changed:
 *     7.1:
 *     This is now a modern ES6-style class and supports typing using
 *     TypeScript.
 */
@spina
export class ReviewDialogCommentHook<
    TAttrs extends ReviewDialogCommentHookAttrs = ReviewDialogCommentHookAttrs,
> extends ExtensionHook<TAttrs> {
    static hookPoint = new ExtensionHookPoint();

    static defaults: Partial<ReviewDialogCommentHookAttrs> = {
        viewType: null,
    };

    /**
     * Set up the hook.
     */
    setUpHook() {
        console.assert(this.get('viewType'),
                       'ReviewDialogCommentHook instance does not have a ' +
                       '"viewType" attribute set.');
    }
}
