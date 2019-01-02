/**
 * A hook for providing callbacks for review request actions.
 *
 * Model Attributes:
 *     callbacks (object):
 *         An object that maps selectors to handlers. When setting up actions
 *         for review requests, the handler will be bound to the "click"
 *         JavaScript event. Defaults to null.
 *
 * Example:
 *     RBSample = {};
 *
 *     (function() {
 *         RBSample.Extension = RB.Extension.extend({
 *             initialize: function () {
 *                 var _onMyNewActionClicked;
 *
 *                 _super(this).initialize.call(this);
 *
 *                 _onMyNewActionClicked = function() {
 *                     if (confirm(gettext('Are you sure?'))) {
 *                         console.log('My new action confirmed! =]');
 *                     }
 *                     else {
 *                         console.log('My new action not confirmed! D=');
 *                     }
 *                 };
 *
 *                 new RB.ReviewRequestActionHook({
 *                     extension: this,
 *                     callbacks: {
 *                        '#my-new-action': _onMyNewActionClicked
 *                     }
 *                 });
 *             }
 *         });
 *     })();
 */
RB.ReviewRequestActionHook = RB.ExtensionHook.extend({
    hookPoint: new RB.ExtensionHookPoint(),

    defaults: _.defaults({
        callbacks: null,
    }, RB.ExtensionHook.prototype.defaults),

    /**
     * Set up the extension hook.
     */
    setUpHook() {
        console.assert(this.get('callbacks'),
                       'ReviewRequestActionHook instance does not have a ' +
                       '"callbacks" attribute set.');
    },
});
