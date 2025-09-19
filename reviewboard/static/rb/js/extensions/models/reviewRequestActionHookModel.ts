/**
 * Extension hook for review request actions.
 *
 * Version Changed:
 *     7.1:
 *     This is now an ESM module supporting TypeScript.
 */

import {
    spina,
} from '@beanbag/spina';

import {
    type ExtensionHookAttrs,
    ExtensionHook,
} from './extensionHookModel';
import {
    ExtensionHookPoint,
} from './extensionHookPointModel';


/**
 * Attributes for ReviewRequestActionHook.
 *
 * Version Added:
 *     7.1
 */
export interface ReviewRequestActionHookAttrs extends ExtensionHookAttrs {
    /**
     * A mapping of selectors to handlers.
     *
     * When setting up actions for review requests, the handler will be
     * bound to the "click" JavaScript event. It defaults to null.
     */
    callbacks: Record<
        string,
        (eventObject: JQuery.TriggeredEvent) => void
    >;
}


/**
 * A hook for providing callbacks for review request actions.
 *
 * Version Changed:
 *     7.1:
 *     This is now a modern ES6-style class and supports typing using
 *     TypeScript.
 *
 * Examples:
 *     .. code-block:: typescript
 *        :caption: TypeScript
 *
 *         import { spina } from '@beanbag/spina';
 *         import {
 *             Extension,
 *             ReviewRequestActionHook,
 *         } from '@beanbag/reviewboard/extensions';
 *
 *
 *         @spina
 *         export class RBSampleExtension extends Extension {
 *             initialize() {
 *                 super.initialize();
 *
 *                 const _onMyNewActionClicked = () => {
 *                 };
 *
 *                 new ReviewRequestActionHook({
 *                     extension: this,
 *                     callbacks: {
 *                         '#my-new-action': () => {
 *                             if (confirm(gettext('Are you sure?'))) {
 *                                 console.log('Confirmed!');
 *                             }
 *                             else {
 *                                 console.log('Not confirmed...');
 *                             }
 *                         },
 *                     },
 *                 });
 *             }
 *         }
 *
 *     .. code-block:: javascript
 *        :caption: JavaScript
 *
 *         RBSample = {};
 *
 *         RBSample.Extension = RB.Extension.extend({
 *             initialize: function() {
 *                 let _onMyNewActionClicked;
 *
 *                 RB.Extension.prototype.initialize.call(this);
 *
 *                 _onMyNewActionClicked = () => {
 *                     if (confirm(gettext('Are you sure?'))) {
 *                         console.log('Confirmed!');
 *                     } else {
 *                         console.log('Not confirmed...');
 *                     }
 *                 };
 *
 *                 new RB.ReviewRequestActionHook({
 *                     extension: this,
 *                     callbacks: {
 *                        '#my-new-action': _onMyNewActionClicked,
 *                     },
 *                 });
 *             },
 *         });
 */
@spina
export class ReviewRequestActionHook<
    TAttrs extends ReviewRequestActionHookAttrs = ReviewRequestActionHookAttrs,
> extends ExtensionHook<TAttrs> {
    static hookPoint = new ExtensionHookPoint();

    static defaults: Partial<ReviewRequestActionHookAttrs> = {
        callbacks: null,
    };

    /**
     * Set up the extension hook.
     */
    setUpHook() {
        console.assert(this.get('callbacks'),
                       'ReviewRequestActionHook instance does not have a ' +
                       '"callbacks" attribute set.');
    }
}
