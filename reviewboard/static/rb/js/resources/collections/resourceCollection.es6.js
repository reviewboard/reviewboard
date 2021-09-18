/**
 * Base collection for resource models.
 *
 * ResourceCollection handles the fetching of models from resource lists
 * in the API.
 *
 * It can do pagination by using fetchNext/fetchPrev. Callers can check
 * hasNext/hasPrev to determine if they've reached the end.
 *
 * To fetch one page at a time, use fetch(). This can take an optional
 * starting point.
 *
 * Use fetchAll to automatically paginate through all items and store them
 * all within the collection.
 */
RB.ResourceCollection = RB.BaseCollection.extend({
    /**
     * Initialize the collection.
     *
     * Args:
     *     models (Array of object):
     *         Initial set of models for the collection.
     *
     *     options (object):
     *         Options for the collection.
     *
     * Option Args:
     *     parentResource (RB.BaseResource):
     *         The parent API resource.
     *
     *     extraQueryData (object):
     *         Additional attributes to include in the API request query
     *         string.
     */
    initialize(models, options) {
        this.parentResource = options.parentResource;
        this.extraQueryData = options.extraQueryData;
        this.maxResults = options.maxResults;
        this.hasPrev = false;
        this.hasNext = false;
        this.currentPage = 0;

        /*
         * Undefined means "we don't know how many results there are."
         * This is a valid value when parsing the payload later. It
         * may also be a number.
         */
        this.totalResults = undefined;

        this._fetchURL = null;
        this._links = null;
    },

    /**
     * Return the URL for fetching models.
     *
     * This will make use of a URL provided by fetchNext/fetchPrev/fetchAll,
     * if provided.
     *
     * Otherwise, this will try to get the URL from the parent resource.
     *
     * Returns:
     *     string:
     *     The URL to fetch.
     */
    url() {
        if (this._fetchURL) {
            return this._fetchURL;
        }

        if (this.parentResource) {
            const links = this.parentResource.get('links');
            const listKey = _.result(this.model.prototype, 'listKey');
            const link = links[listKey];

            return link ? link.href : null;
        }

        return null;
    },

    /**
     * Parse the results from the list payload.
     *
     * Args:
     *     rsp (object):
     *         The response from the server.
     *
     *     options (object):
     *         The options that were used for the fetch operation.
     *
     * Option Args:
     *     fetchingAll (boolean):
     *         Whether we're in the process of fetching all the items.
     *
     *     page (number):
     *         The page of results that were fetched.
     */
    parse(rsp, options={}) {
        const listKey = _.result(this.model.prototype, 'listKey');

        this._links = rsp.links || null;
        this.totalResults = rsp.total_results;

        if (options.fetchingAll) {
            this.hasPrev = false;
            this.hasNext = false;
            this.currentPage = 0;
        } else {
            this.totalResults = rsp.total_results;
            this.hasPrev = (this._links !== null &&
                            this._links.prev !== undefined);
            this.hasNext = (this._links !== null &&
                            this._links.next !== undefined);
            this.currentPage = options.page;
        }

        return rsp[listKey];
    },

    /**
     * Fetch models from the list.
     *
     * By default, this will replace the list of models in this collection.
     * That can be changed by providing `reset: false` in options.
     *
     * The first page of resources will be fetched unless options.start is
     * set. The value is the start position for the number of objects, not
     * pages.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object):
     *         Options for the fetch operation.
     *
     *     context (object):
     *         Context to be used when calling callbacks.
     *
     * Option Args:
     *     start (string):
     *         The start position to use when fetching paginated results.
     *
     *     maxResults (number):
     *         The number of results to return.
     *
     *     reset (boolean):
     *         Whether the collection should be reset with the newly-fetched
     *         items, or those items should be appended to the collection.
     *
     *     data (object):
     *         Data to pass to the API request.
     *
     *     success (function):
     *         Callback to be called when the fetch is successful.
     *
     *     error (function):
     *         Callback to be called when the fetch fails.
     *
     *     complete (function):
     *         Callback to be called after either success or error.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the fetch operation is complete.
     */
    fetch: async function(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ResourceCollection.fetch was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.fetch(newOptions));
        }

        const data = _.extend({}, options.data);

        if (options.start !== undefined) {
            data.start = options.start;
        }

        /*
         * There's a couple different ways that the max number of results
         * can be specified. We'll want to support them all.
         *
         * If a value is passed in extraQueryData, it takes precedence.
         * We'll just set it further down. Otherwise, options.maxResults
         * will be used if passed, falling back on the maxResults passed
         * during collection construction.
         */
        if (!this.extraQueryData ||
            this.extraQueryData['max-results'] === undefined) {
            if (options.maxResults !== undefined) {
                data['max-results'] = options.maxResults;
            } else if (this.maxResults) {
                data['max-results'] = this.maxResults;
            }
        }

        if (options.reset === undefined) {
            options.reset = true;
        }

        /*
         * Versions of Backbone prior to 1.1 won't respect the reset option,
         * instead requiring we use 'remove'. Support this for compatibility,
         * until we move to Backbone 1.1.
         */
        options.remove = options.reset;

        const expandedFields = this.model.prototype.expandedFields;
        if (expandedFields.length > 0) {
            data.expand = expandedFields.join(',');
        }

        if (this.extraQueryData) {
            _.defaults(data, this.extraQueryData);
        }

        options.data = data;

        if (this.parentResource) {
            await this.parentResource.ready();
        }

        await RB.BaseCollection.prototype.fetch.call(this, options);
    },

    /**
     * Fetch the previous batch of models from the resource list.
     *
     * This requires hasPrev to be true, from a prior fetch.
     *
     * The collection's list of models will be replaced with the new list
     * after the fetch succeeds. Each time fetchPrev is called, the collection
     * will consist only of that page's batch of models. This can be overridden
     * by providing `reset: false` in options.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object):
     *         Options for the fetch operation.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    fetchPrev(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ResourceCollection.fetchPrev was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.fetchPrev(newOptions));
        }

        if (!this.hasPrev) {
            return Promise.resolve();
        }

        this._fetchURL = this._links.prev.href;

        return this.fetch(
            _.defaults({
                page: this.currentPage - 1
            }, options));
    },

    /**
     * Fetch the next batch of models from the resource list.
     *
     * This requires hasNext to be true, from a prior fetch.
     *
     * The collection's list of models will be replaced with the new list
     * after the fetch succeeds. Each time fetchNext is called, the collection
     * will consist only of that page's batch of models. This can be overridden
     * by providing `reset: false` in options.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object):
     *         Options for the fetch operation.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    fetchNext(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ResourceCollection.fetchNext was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.fetchNext(newOptions));
        }

        if (!this.hasNext && options.enforceHasNext !== false) {
            return Promise.resolve();
        }

        this._fetchURL = this._links.next.href;

        return this.fetch(
            _.defaults({
                page: this.currentPage + 1
            }, options));
    },

    /**
     * Fetch all models from the resource list.
     *
     * This will fetch all the models from a resource list on a server,
     * paginating automatically until all models are fetched. The result is
     * a list of models on the server.
     *
     * This differs from fetch/fetchPrev/fetchNext, which will replace the
     * collection each time a page of resources are loaded.
     *
     * This can end up slowing down the server. Use it carefully.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object):
     *         Options for the fetch operation.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async fetchAll(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ResourceCollection.fetchNext was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.fetchAll(newOptions));
        }

        const fetchOptions = _.defaults({
            reset: false,
            fetchingAll: true,
            enforceHasNext: false,
            maxResults: 50,
        }, options);

        this._fetchURL = null;

        this.reset();

        await this.fetch(fetchOptions);

        while (this._links.next) {
            await this.fetchNext(fetchOptions);
        }
    },

    /**
     * Prepare the model for the collection.
     *
     * This overrides Collection's _prepareModel to ensure that the resource
     * has the proper parentObject set.
     *
     * Returns:
     *     Backbone.Model:
     *     The new model.
     */
    _prepareModel() {
        const model = RB.BaseCollection.prototype._prepareModel.apply(this, arguments);

        model.set('parentObject', this.parentResource);

        return model;
    },
});
