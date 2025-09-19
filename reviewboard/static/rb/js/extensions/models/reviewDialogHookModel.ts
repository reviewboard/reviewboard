/**
 * Extension hook for extending the Review Dialog.
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
    type BaseReviewDialogHookViewClass,
} from '../views/baseReviewDialogHookView';


/**
 * Attributes for ReviewDialogHook.
 *
 * Version Added:
 *     7.1
 */
export interface ReviewDialogHookAttrs extends ExtensionHookAttrs {
    /** The view type to construct in the Review Dialog. */
    viewType: BaseReviewDialogHookViewClass;
}


/**
 * Adds additional rendering or UI to the top of the review dialog.
 *
 * This can be used to display additional UI and even additional fields in
 * the review dialog before all comments, below the Ship It checkbox.
 *
 * A Backbone View type (not an instance) must be provided for the viewType
 * attribute. When rendering comments in the dialog, an instance of the
 * provided view will be created and passed the comment as the view's model.
 *
 * Version Changed:
 *     7.1:
 *     This is now a modern ES6-style class and supports typing using
 *     TypeScript.
 */
@spina
export class ReviewDialogHook<
    TAttrs extends ReviewDialogHookAttrs = ReviewDialogHookAttrs,
> extends ExtensionHook<TAttrs> {
    static hookPoint = new ExtensionHookPoint();

    static defaults: Partial<ReviewDialogHookAttrs> = {
        viewType: null,
    };

    /**
     * Set up the hook.
     */
    setUpHook() {
        console.assert(this.get('viewType'),
                       'ReviewDialogHook instance does not have a ' +
                       '"viewType" attribute set.');
    }
}
