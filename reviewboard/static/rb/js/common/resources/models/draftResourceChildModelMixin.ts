/** Mixin for resources that are children of a draft resource. */

import { type ReadyOptions } from './baseResourceModel';


/**
 * Mixin for resources that are children of a draft resource.
 *
 * This will ensure that the draft is in a proper state before operating
 * on the resource.
 */
export const DraftResourceChildModelMixin = {
    /**
     * Delete the object's resource on the server.
     *
     * This will ensure the draft is created before deleting the object,
     * in order to record the deletion as part of the draft.
     *
     * Version Changed:
     *     8.0:
     *     Removed callbacks and the context parameter.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
     *
     * Args:
     *     options (object, optional):
     *         Options for the operation, including callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async destroy(
        options: Backbone.ModelDestroyOptions = {},
    ): Promise<void> {
        console.assert(
            !(options.success || options.error || options.complete),
            dedent`
                RB.DraftResourceChildModelMixin.destroy was called using
                callbacks. This has been removed in Review Board 8.0 in favor
                of promises.
            `);

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
     *     8.0:
     *     Removed callbacks and the context parameter.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
     *
     * Args:
     *     options (object, optional):
     *         Options for the operation, including callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async ready(
        options: ReadyOptions = {},
        context: object = undefined,
    ): Promise<void> {
        console.assert(
            !(options.success || options.error || options.complete ||
              options.ready),
            dedent`
                RB.DraftResourceChildModelMixin.ready was called using
                callbacks. This has been removed in Review Board 8.0 in favor
                of promises.
            `);

        await this.get('parentObject').ensureCreated();
        await _super(this).ready.call(this);
    },
};
