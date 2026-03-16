/**
 * The base class used for Review Board collections.
 * */
import { BaseCollection as SpinaCollection, spina } from '@beanbag/spina';

import {
    API,
    BackboneError,
} from '../utils/apiUtils';


/**
 * The base class used for Review Board collections.
 *
 * This is a thin subclass over Backbone.Collection that just provides
 * some useful additional abilities.
 */
@spina
export class BaseCollection<
    TModel extends Backbone.Model = Backbone.Model,
    TExtraCollectionOptions = unknown,
    TCollectionOptions = Backbone.CollectionOptions<TModel>
> extends SpinaCollection<
    TModel,
    TExtraCollectionOptions,
    TCollectionOptions
> {
    /**
     * Fetch models from the server.
     *
     * This behaves just like Backbone.Collection.fetch, except it
     * takes a context parameter for callbacks and can return promises.
     *
     * Version Changed:
     *     8.0:
     *     Removed callbacks and the context parameter.
     *
     * Version Changed:
     *     5.0:
     *     This method was changed to return a promise. Using callbacks instead
     *     of the promise is deprecated.
     *
     * Args:
     *     options (object):
     *         Options for the fetch operation.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the fetch operation is complete.
     */
    fetch(
        options: Backbone.CollectionFetchOptions = {},
    ): Promise<BaseCollection> {
        console.assert(
            !(options.success || options.error),
            dedent`
                RB.BaseCollection.fetch was called using callbacks. This has
                been removed in Review Board 8.0 in favor of promises.
            `);

        return new Promise((resolve, reject) => {
            super.fetch(_.defaults({
                error: (model, xhr, options) => reject(
                    new BackboneError(model, xhr, options)),
                success: result => resolve(result),
            }, options));
        });
    }

    /**
     * Handle all AJAX communication for the collection.
     *
     * Backbone.js will internally call the model's sync function to
     * communicate with the server, which usually uses Backbone.sync.
     *
     * This will parse error response from Review Board so we can provide
     * a more meaningful error callback.
     *
     * Args:
     *     method (string):
     *         The HTTP method to use for the AJAX request.
     *
     *     model (object):
     *         The model to sync.
     *
     *     options (object):
     *         Options for the sync operation.
     */
    sync(
        method: string,
        model: BaseCollection,
        options: JQuery.AjaxSettings = {},
    ) {
        return Backbone.sync.call(this, method, model, _.defaults({
            error: (xhr, textStatus, errorThrown) => {
                API.storeError(xhr);

                if (_.isFunction(options.error)) {
                    options.error(xhr, textStatus, errorThrown);
                }
            },
        }, options));
    }
}
