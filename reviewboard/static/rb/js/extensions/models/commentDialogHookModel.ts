/**
 * Extension hook for extending the comment dialog.
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
import {
    ExtensionHookPoint,
} from './extensionHookPointModel';
import {
    type BaseCommentDialogHookViewClass,
} from '../views/baseCommentDialogHookView';


/**
 * Attributes for CommentDialogHook.
 *
 * Version Added:
 *     7.1
 */
export interface CommentDialogHookAttrs extends ExtensionHookAttrs {
    /** The view type to construct in the comment dialog. */
    viewType: BaseCommentDialogHookViewClass;
}


/**
 * Provides extensibility for the Comment Dialog.
 *
 * Users of this hook can provide a Backbone View that will have access to
 * the CommentDialog and its CommentEditor (through the commentDialog and
 * commentEditor options passed to the view). They can call public API on
 * the comment dialog and augment the contents of the dialog.
 *
 * Version Changed:
 *     7.1:
 *     This is now a modern ES6-style class and supports typing using
 *     TypeScript.
 */
@spina
export class CommentDialogHook<
    TAttrs extends CommentDialogHookAttrs = CommentDialogHookAttrs,
> extends ExtensionHook<TAttrs> {
    static hookPoint = new ExtensionHookPoint();

    static defaults: Partial<CommentDialogHookAttrs> = {
        viewType: null,
    };

    /**
     * Set up the hook.
     */
    setUpHook() {
        console.assert(this.get('viewType'),
                       'CommentDialogHook instance does not have a ' +
                       '"viewType" attribute set.');
    }
}
