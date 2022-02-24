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
    async destroy(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.DraftResourceChildModelMixin.destroy was ' +
                         'called using callbacks. Callers should be updated ' +
                         'to use promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.destroy(newOptions));
        }

        await this.get('parentObject').ensureCreated();
        await _super(this).destroy.call(this, options);
    },

    /**
     * Call a function when the object is ready to use.
     *
     * This will ensure the draft is created before ensuring the object
     * is ready.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
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
    async ready(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete) ||
            _.isFunction(options.ready)) {
            console.warn('RB.DraftResourceChildModelMixin.ready was ' +
                         'called using callbacks. Callers should be updated ' +
                         'to use promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.ready());
        }

        await this.get('parentObject').ensureCreated();
        await _super(this).ready.call(this);
    },
};
