/**
 * Mixin for resources that have special "draft" URLs.
 *
 * Some resources contain a "draft/" singleton URL that will either redirect to
 * the URL for an existing draft, or indicate there's no draft (and requiring
 * that one be created).
 *
 * These resources need a little more logic to look up the draft state and
 * craft the proper URL. They can use this mixin to do that work for them.
 */
RB.DraftResourceModelMixin = {
    /**
     * Call a function when the object is ready to use.
     *
     * If the object is unloaded, we'll likely need to grab the draft
     * resource, particularly if we haven't already retrieved a draft.
     *
     * Otherwise, we delegate to the parent's ready().
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
            console.warn('RB.DraftResourceModelMixin.ready was ' +
                         'called using callbacks. Callers should be updated ' +
                         'to use promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.ready(newOptions));
        }

        if (!this.get('loaded') && this.isNew() &&
            this._needDraft === undefined) {
            this._needDraft = true;
        }

        await _super(this).ready.call(this);

        if (this._needDraft) {
            /*
             * Start by delegating to the parent ready() function. Because the
             * object is "new", this will make sure that the parentObject is
             * ready.
             */
            await this._retrieveDraft(options);
        }
    },

    /**
     * Destroy the object.
     *
     * If destruction is successful, we'll reset the needDraft state so we'll
     * look up the draft the next time an operation is performed.
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
    async destroy(options={}, context=undefined) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.DraftResourceModelMixin.destroy was ' +
                         'called using callbacks. Callers should be updated ' +
                         'to use promises instead.');
            return RB.promiseToCallbacks(
                options, context, newOptions => this.destroy(newOptions));
        }

        await this.ready();
        await _super(this).destroy.call(this, options);

        /* We need to fetch the draft resource again. */
        this._needDraft = true;
    },

    /**
     * Return the URL to use when syncing the model.
     *
     * Custom URL implementation which will return the special draft resource
     * if we have yet to redirect and otherwise delegate to the prototype
     * implementation.
     *
     * Returns:
     *     string:
     *     The URL to use for the resource.
     */
    url() {
        if (this._needDraft) {
            const parentObject = this.get('parentObject');
            const linkName = _.result(this, 'listKey');
            const links = parentObject.get('links');

            /*
             * Chrome hyper-aggressively caches things it shouldn't, and
             * appears to do so in a subtly broken way.
             *
             * If we do a DELETE on a reply's URL, then later a GET (resulting
             * from a redirect from a GET to draft/), Chrome will somehow get
             * confused and associate the GET's caching information with a 404.
             *
             * In order to prevent this, we need to make requests to draft/
             * appear unique. We can do this by appending the timestamp here.
             * Chrome will no longer end up with broken state for our later
             * GETs.
             *
             * Much of this is only required in the case of sqlite, which,
             * with Django, may reuse row IDs, causing problems when making
             * a reply, deleting, and making a new one. In production, this
             * shouldn't be a problem, but it's very confusing during
             * development.
             */
            return links[linkName].href + 'draft/?' + $.now();
        } else {
            return _super(this).url.call(this);
        }
    },

    /**
     * Try to retrieve an existing draft from the server.
     *
     * This uses the special draft/ resource within the resource list, which
     * will redirect to an existing draft if one exists.
     *
     * Args:
     *     options (object):
     *         Options for the operation, including callbacks.
     */
    _retrieveDraft(options) {
        if (!RB.UserSession.instance.get('authenticated')) {
            return Promise.reject(new BackboneError(
                this,
                { errorText: gettext('You must be logged in to retrieve the draft.') },
                {}));
        }

        let data = options.data || {};
        const extraQueryArgs = _.result(this, 'extraQueryArgs', {});

        if (!_.isEmpty(extraQueryArgs)) {
            data = _.extend({}, extraQueryArgs, data);
        }

        return new Promise((resolve, reject) => {
            Backbone.Model.prototype.fetch.call(this, {
                data: data,
                processData: true,
                success: () => {
                    /*
                     * There was an existing draft, and we were redirected to it
                     * and pulled data from it. We're done.
                     */
                    this._needDraft = false;

                    resolve();
                },
                error: (model, xhr, options) => {
                    if (xhr.status === 404) {
                        /*
                         * We now know we don't have an existing draft to work with,
                         * and will eventually need to POST to create a new one.
                         */
                        this._needDraft = false;
                        resolve();
                    } else {
                        reject(new BackboneError(model, xhr, options));
                    }
                }
            });
        });
    },
};
