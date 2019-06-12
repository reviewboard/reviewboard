/**
 * Adds additional rendering or UI for a comment in the review dialog.
 *
 * This can be used to display additional UI and even additional fields in
 * the review dialog, which can reflect and potentially modify extra data
 * for a comment.
 *
 * A Backbone View type (not an instance) must be provided for the viewType
 * attribute. When rendering comments in the dialog, an instance of the
 * provided view will be created and passed the comment as the view's model.
 */
RB.ReviewDialogCommentHook = RB.ExtensionHook.extend({
    hookPoint: new RB.ExtensionHookPoint(),

    defaults: _.defaults({
        viewType: null,
    }, RB.ExtensionHook.prototype.defaults),

    /**
     * Set up the hook.
     */
    setUpHook() {
        console.assert(this.get('viewType'),
                       'ReviewDialogCommentHook instance does not have a ' +
                       '"viewType" attribute set.');
    },
});
