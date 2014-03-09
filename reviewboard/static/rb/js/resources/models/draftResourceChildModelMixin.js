/*
 * Mixin for resources that are children of a draft resource.
 *
 * This will ensure that the draft is in a proper state before operating
 * on the resource.
 */
RB.DraftResourceChildModelMixin = {
    /*
     * Deletes the object's resource on the server.
     *
     * This will ensure the draft is created before deleting the object,
     * in order to record the deletion as part of the draft.
     */
    destroy: function(options, context) {
        options = options || {};

        this.get('parentObject').ensureCreated({
            success: _.bind(_super(this).destroy, this, options, context),
            error: options.error
        }, context);
    },

    /*
     * Calls a function when the object is ready to use.
     *
     * This will ensure the draft is created before ensuring the object
     * is ready.
     */
    ready: function(options, context) {
        options = options || {};

        this.get('parentObject').ensureCreated({
            success: _.bind(_super(this).ready, this, options, context),
            error: options.error
        }, context);
    }
};
