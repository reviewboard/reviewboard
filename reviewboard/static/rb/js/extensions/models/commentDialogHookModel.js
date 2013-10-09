/*
 * Provides extensibility for the Comment Dialog.
 *
 * Users of this hook can provide a Backbone View that will have access to
 * the CommentDialog and its CommentEditor (through the commentDialog and
 * commentEditor options passed to the view). They can call public API on
 * the comment dialog and augment the contents of the dialog.
 */
RB.CommentDialogHook = RB.ExtensionHook.extend({
    hookPoint: new RB.ExtensionHookPoint(),

    defaults: _.defaults({
        viewType: null
    }, RB.ExtensionHook.prototype.defaults),

    setUpHook: function() {
        console.assert(this.get('viewType'),
                       'CommentDialogHook instance does not have a ' +
                       '"viewType" attribute set.');
    }
});
