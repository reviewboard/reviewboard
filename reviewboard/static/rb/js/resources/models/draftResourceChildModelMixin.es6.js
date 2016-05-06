/**
 * Mixin for resources that are children of a draft resource.
 *
 * This will ensure that the draft is in a proper state before operating
 * on the resource.
 */
RB.DraftResourceChildModelMixin = {
    /**
     * Delete the object's resource on the server.
     *
     * This will ensure the draft is created before deleting the object,
     * in order to record the deletion as part of the draft.
     *
     * Args:
     *     options (object):
     *         Options for the operation, including callbacks.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    destroy(options={}, context=undefined) {
        this.get('parentObject').ensureCreated({
            success: _super(this).destroy.bind(this, options, context),
            error: options.error
        }, context);
    },

    /**
     * Call a function when the object is ready to use.
     *
     * This will ensure the draft is created before ensuring the object
     * is ready.
     *
     * Args:
     *     options (object):
     *         Options for the operation, including callbacks.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    ready(options={}, context=undefined) {
        this.get('parentObject').ensureCreated({
            success: _super(this).ready.bind(this, options, context),
            error: options.error
        }, context);
    }
};
