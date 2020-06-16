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
     *     options (object, optional):
     *         Options for the operation, including callbacks.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    destroy(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.DraftResourceChildModelMixin.destroy was ' +
                         'called using callbacks. Callers should be updated ' +
                         'to use promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.destroy(newOptions));
        }

        return new Promise((resolve, reject) => {
            this.get('parentObject').ensureCreated({
                success: () => resolve(
                    _super(this).destroy.call(this, options)),
                error: (model, xhr, options) => reject(
                    new BackboneError(model, xhr, options)),
            });
        });
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
