/*
 * Adds additional rendering or UI to the top of the review dialog.
 *
 * This can be used to display additional UI and even additional fields in
 * the review dialog before all comments, below the Ship It checkbox.
 *
 * A Backbone View type (not an instance) must be provided for the viewType
 * attribute. When rendering comments in the dialog, an instance of the
 * provided view will be created and passed the comment as the view's model.
 */
RB.ReviewDialogHook = RB.ExtensionHook.extend({
    hookPoint: new RB.ExtensionHookPoint(),

    defaults: _.defaults({
        viewType: null
    }, RB.ExtensionHook.prototype.defaults),

    setUpHook: function() {
        console.assert(this.get('viewType'),
                       'ReviewDialogHook instance does not have a ' +
                       '"viewType" attribute set.');
    }
});
