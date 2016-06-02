/**
 * The base model for all API-backed resource models.
 *
 * This provides a common set of attributes and functionality for working
 * with Review Board's REST API. That includes fetching data for a known
 * resource, creating resources, saving, deleting, and navigating children
 * resources by way of a payload's list of links.
 *
 * Other resource models are expected to extend this. In particular, they
 * should generally be extending toJSON() and parse().
 */
RB.BaseResource = Backbone.Model.extend({
    /**
     * Return default values for the model attributes.
     *
     * Returns:
     *     object:
     *     The attribute defaults.
     */
    defaults() {
        return {
            extraData: {},
            links: null,
            loaded: false,
            parentObject: null
        };
    },

    /** The key for the namespace for the object's payload in a response. */
    rspNamespace: '',

    /** The attribute used for the ID in the URL. */
    urlIDAttr: 'id',

    listKey() {
        return this.rspNamespace + 's';
    },

    /** The list of fields to expand in resource payloads. */
    expandedFields: [],

    /**
     * Extra query arguments for GET requests.
     *
     * This may also be a function that returns the extra query arguments.
     *
     * These values can be overridden by the caller when making a request.
     * They function as defaults for the queries.
     */
    extraQueryArgs: {},

    /** Whether or not extra data can be associated on the resource. */
    supportsExtraData: false,

    /**
     * A map of attribute names to resulting JSON field names.
     *
     * This is used to auto-generate a JSON payload from attribute names
     * in toJSON().
     *
     * It's also needed if using attribute names in any save({attrs: [...]})
     * calls.
     */
    attrToJsonMap: {},

    /** A list of attributes to serialize in toJSON(). */
    serializedAttrs: [],

    /** A list of attributes to deserialize in parseResourceData(). */
    deserializedAttrs: [],

    /** Special serializer functions called in toJSON(). */
    serializers: {},

    /** Special deserializer functions called in parseResourceData(). */
    deserializers: {},

    /**
     * Initialize the model.
     */
    initialize() {
        if (this.supportsExtraData) {
            this._setupExtraData();
        }
    },

    /**
     * Return the URL for this resource's instance.
     *
     * If this resource is loaded and has a URL to itself, that URL will
     * be returned. If not yet loaded, it'll try to get it from its parent
     * object, if any.
     *
     * Returns:
     *     string:
     *     The URL to use when fetching the resource. If the URL cannot be
     *     determined, this will return null.
     */
    url() {
        let links = this.get('links');

        if (links) {
            return links.self.href;
        }

        const parentObject = this.get('parentObject');

        if (parentObject) {
            links = parentObject.get('links');

            if (links) {
                const key = _.result(this, 'listKey');
                const link = links[key];

                if (link) {
                    const baseURL = link.href;

                    return this.isNew()
                           ? baseURL
                           : (baseURL + this.get(this.urlIDAttr) + '/');
                }
            }
        }

        return null;
    },

    /**
     * Call a function when the object is ready to use.
     *
     * An object is ready it has an ID and is loaded, or is a new resource.
     *
     * When the object is ready, options.ready() will be called. This may
     * be called immediately, or after one or more round trips to the server.
     *
     * If we fail to load the resource, objects.error() will be called instead.
     *
     * Args:
     *     options (object):
     *         Options for the fetch operation.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     *
     * Option Args:
     *     ready (function):
     *         Callback function for when the object is ready to use.
     *
     *     error (function):
     *         Callback function for when an error occurs.
     */
    ready(options={}, context=undefined) {
        const success = _.isFunction(options.ready)
                        ? _.bind(options.ready, context)
                        : undefined;
        const error = _.isFunction(options.error)
                      ? _.bind(options.error, context)
                      : undefined;

        const parentObject = this.get('parentObject');

        if (this.get('loaded')) {
            // We already have data--just call the callbacks
            if (success) {
                success();
            }
        } else if (!this.isNew()) {
            // Fetch data from the server
            this.fetch({
                data: options.data,
                success: success,
                error: error
            });
        } else if (parentObject) {
            /*
             * This is a new object, which means there's nothing to fetch from
             * the server, but we still need to ensure that the parent is loaded
             * in order for it to have valid links.
             */
            parentObject.ready({
                ready: success,
                error: error
            });
        } else if (success) {
            // Fallback for dummy objects.
            success();
        }
    },

    /**
     * Call a function when we know an object exists server-side.
     *
     * This works like ready() in that it's used to delay operating on the
     * resource until we have a server-side representation. Unlike ready(),
     * it will attempt to create it if it doesn't exist first.
     *
     * When the object has been created, or we know it already is,
     * options.success() will be called.
     *
     * If we fail to create the object, options.error() will be called
     * instead.
     *
     * Args:
     *     options (object):
     *         Object with success and error callbacks.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     */
    ensureCreated(options={}, context=undefined) {
        this.ready({
            ready: () => {
                if (!this.get('loaded')) {
                    this.save({
                        success: _.isFunction(options.success)
                                 ? _.bind(options.success, context)
                                 : undefined,
                        error: _.isFunction(options.error)
                               ? _.bind(options.error, context)
                               : undefined
                    });
                } else if (_.isFunction(options.success)) {
                    options.success.call(context);
                }
            }
        });
    },

    /**
     * Fetch the object's data from the server.
     *
     * An object must have an ID before it can be fetched. Otherwise,
     * options.error() will be called.
     *
     * If this has a parent resource object, we'll ensure that's ready before
     * fetching this resource.
     *
     * The resource must override the parse() function to determine how
     * the returned resource data is parsed and what data is stored in
     * this object.
     *
     * If we successfully fetch the resource, options.success() will be
     * called.
     *
     * If we fail to fetch the resource, options.error() will be called.
     *
     * Args:
     *     options (object):
     *         Object with success and error callbacks.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     */
    fetch(options={}, context=undefined) {
        options = _.bindCallbacks(options, context);

        if (this.isNew()) {
            if (_.isFunction(options.error)) {
                options.error.call(context,
                    'fetch cannot be used on a resource without an ID');
            }

            return;
        }

        const parentObject = this.get('parentObject');

        if (parentObject) {
            parentObject.ready({
                ready: () => Backbone.Model.prototype.fetch.call(this, options),
                error: options.error
            }, this);
        } else {
            Backbone.Model.prototype.fetch.call(this, options);
        }
    },

    /**
     * Save the object's data to the server.
     *
     * If the object has an ID already, it will be saved to its known
     * URL using HTTP PUT. If it doesn't have an ID, it will be saved
     * to its parent list resource using HTTP POST
     *
     * If this has a parent resource object, we'll ensure that's created
     * before saving this resource.
     *
     * An object must either be loaded or have a parent resource linking to
     * this object's list resource URL for an object to be saved.
     *
     * The resource must override the toJSON() function to determine what
     * data is saved to the server.
     *
     * If we successfully save the resource, options.success() will be
     * called, and the "saved" event will be triggered.
     *
     * If we fail to save the resource, options.error() will be called.
     *
     * Args:
     *     options (object):
     *         Object with success and error callbacks.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     */
    save(options={}, context=undefined) {
        this.trigger('saving', options);

        this.ready({
            ready: () => {
                const parentObject = this.get('parentObject');

                if (parentObject) {
                    parentObject.ensureCreated({
                        success: this._saveObject.bind(this, options, context),
                        error: options.error
                    }, this);
                } else {
                    this._saveObject(options, context);
                }
            },
            error: _.isFunction(options.error)
                   ? _.bind(options.error, context)
                   : undefined
        }, this);
    },

    /**
     * Handle the actual saving of the object's state.
     *
     * This is called internally by save() once we've handled all the
     * readiness and creation checks of this object and its parent.
     *
     * Args:
     *     options (object):
     *         Object with success and error callbacks.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     */
    _saveObject(options, context) {
        const url = _.result(this, 'url');
        if (!url) {
            if (_.isFunction(options.error)) {
                options.error.call(context,
                    'The object must either be loaded from the server or ' +
                    'have a parent object before it can be saved');
            }

            return;
        }

        const saveOptions = _.defaults({
            success: (...args) => {
                if (_.isFunction(options.success)) {
                    options.success.apply(context, args);
                }

                this.trigger('saved', options);
            },
            error: (...args) => {
                if (_.isFunction(options.error)) {
                    options.error.apply(context, args);
                }

                this.trigger('saveFailed', options);
            }
        }, options);

        saveOptions.attrs = options.attrs || this.toJSON(options);

        const files = [];
        const readers = [];

        if (!options.form) {
            if (this.payloadFileKeys && window.File) {
                /* See if there are files in the attributes we're using. */
                this.payloadFileKeys.forEach(key => {
                    const file = saveOptions.attrs[key];

                    if (file) {
                        files.push(file);
                    }
                });
            }
        }

        if (files.length > 0) {
            files.forEach(file => {
                const reader = new FileReader();

                readers.push(reader);
                reader.onloadend = () => {
                    if (readers.every(r => r.readyState === FileReader.DONE)) {
                        this._saveWithFiles(files, readers, saveOptions);
                    }
                };
                reader.readAsArrayBuffer(file);
            });
        } else {
            Backbone.Model.prototype.save.call(this, {}, saveOptions);
        }
    },

    /**
     * Save the model with a file upload.
     *
     * When doing file uploads, we need to hand-structure a form-data payload
     * to the server. It will contain the file contents and the attributes
     * we're saving. We can then call the standard save function with this
     * payload as our data.
     *
     * Args:
     *     files (Array of object):
     *         A list of files, with ``name`` and ``type`` keys.
     *
     *     fileReaders (Array of FileReader):
     *         Readers corresponding to each item in ``files``.
     *
     *     options (object):
     *         Options for the save operation.
     *
     * Option Args:
     *     boundary (string):
     *         Optional MIME multipart boundary.
     *
     *     attrs (object):
     *         Additional key/value pairs to include in the payload data.
     */
    _saveWithFiles(files, fileReaders, options) {
        const boundary = options.boundary ||
                         ('-----multipartformboundary' + new Date().getTime());
        const blob = [];

        for (let [key, file, reader] of
             _.zip(this.payloadFileKeys, files, fileReaders)) {
            if (!file || !reader) {
                continue;
            }

            blob.push('--' + boundary + '\r\n');
            blob.push('Content-Disposition: form-data; name="' +
                      key + '"; filename="' + file.name + '"\r\n');
            blob.push('Content-Type: ' + file.type + '\r\n');
            blob.push('\r\n');

            blob.push(reader.result);

            blob.push('\r\n');
        }

        for (let [key, value] of Object.entries(options.attrs)) {
            if (!this.payloadFileKeys.includes(key) &&
                value !== undefined &&
                value !== null) {
                blob.push('--' + boundary + '\r\n');
                blob.push('Content-Disposition: form-data; name="' + key +
                          '"\r\n');
                blob.push('\r\n');
                blob.push(value + '\r\n');
            }
        }

        blob.push('--' + boundary + '--\r\n\r\n');

        Backbone.Model.prototype.save.call(this, {}, _.extend({
            data: new Blob(blob),
            processData: false,
            contentType: 'multipart/form-data; boundary=' + boundary,
        }, options));
    },

    /**
     * Delete the object's resource on the server.
     *
     * An object must either be loaded or have a parent resource linking to
     * this object's list resource URL for an object to be deleted.
     *
     * Args:
     *     options (object):
     *         Object with success and error callbacks.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     */
    destroy(options={}, context=undefined) {
        options = _.bindCallbacks(options, context);

        this.trigger('destroying', options);

        const parentObject = this.get('parentObject');

        if (!this.isNew() && parentObject) {
            /*
             * XXX This is temporary to support older-style resource
             *     objects. We should just use ready() once we're moved
             *     entirely onto BaseResource.
             */
            parentObject.ready(_.defaults({
                ready: () => this._destroyObject(options, context)
            }, options));
        } else {
            this._destroyObject(options, context);
        }
    },

    /**
     * Set up the deletion of the object.
     *
     * This is called internally by destroy() once we've handled all the
     * readiness and creation checks of this object and its parent.
     *
     * Once we've done some work to ensure the URL is valid and the object
     * is ready, we'll finish destruction by calling _finishDestroy.
     *
     * Args:
     *     options (object):
     *         Object with success and error callbacks.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     */
    _destroyObject(options={}, context=null) {
        const url = _.result(this, 'url');

        if (!url) {
            if (this.isNew()) {
                /*
                 * If both this resource and its parent are new, it's possible
                 * that we'll get through here without a url. In this case, all
                 * the data is still local to the client and there's not much to
                 * clean up; just call Model.destroy and be done with it.
                 */
                this._finishDestroy(options, context);
            } else if (_.isFunction(options.error)) {
                options.error.call(context,
                    'The object must either be loaded from the server or ' +
                    'have a parent object before it can be deleted');
            }

            return;
        }

        this.ready({
            ready: () => this._finishDestroy(options, context),
            error: _.isFunction(options.error)
                   ? _.bind(options.error, context)
                   : undefined
        }, this);
    },

    /**
     * Finish destruction of the object.
     *
     * This will call the parent destroy method, then reset the state
     * of the object on success.
     *
     * Args:
     *     options (object):
     *         Object with success and error callbacks.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     */
    _finishDestroy(options, context) {
        const parentObject = this.get('parentObject');

        Backbone.Model.prototype.destroy.call(this, _.defaults({
            wait: true,
            success: (...args) => {
                /*
                 * Reset the object so it's new again, but with the same
                 * parentObject.
                 */
                this.set(_.defaults(
                    {
                        id: null,
                        parentObject: parentObject
                    },
                    _.result(this, 'defaults')));

                this.trigger('destroyed', options);

                if (_.isFunction(options.success)) {
                    options.success.apply(context, args);
                }
            }
        }, _.bindCallbacks(options, context)));
    },

    /**
     * Parse and returns the payload from an API response.
     *
     * This will by default only return the object's ID and list of links.
     * Subclasses should override this to return any additional data that's
     * needed, but they must include the results of
     * BaseResource.protoype.parse as well.
     *
     * Args:
     *     rsp (object):
     *         The payload received from the server.
     *
     * Returns:
     *     object:
     *     Attributes to set on the model.
     */
    parse(rsp) {
        console.assert(this.rspNamespace,
                       'rspNamespace must be defined on the resource model');

        if (rsp.stat !== undefined) {
            /*
             * This resource payload is inside an envelope from an API
             * call. It's not model construction data or from a list
             * resource.
             */
            rsp = rsp[this.rspNamespace];
        }

        return _.defaults({
            extraData: rsp.extra_data,
            id: rsp.id,
            links: rsp.links,
            loaded: true
        }, this.parseResourceData(rsp));
    },

    /*
     * Parse the resource data from a payload.
     *
     * By default, this will make use of attrToJsonMap and any
     * jsonDeserializers to construct a resulting set of attributes.
     *
     * This can be overridden by subclasses.
     *
     * Args:
     *     rsp (object):
     *         The payload received from the server.
     *
     * Returns:
     *     object:
     *     Attributes to set on the model.
     */
    parseResourceData(rsp) {
        const attrs = {};

        for (let attrName of this.deserializedAttrs) {
            const deserializer = this.deserializers[attrName];
            const jsonField = this.attrToJsonMap[attrName] || attrName;
            let value = rsp[jsonField];

            if (deserializer) {
                value = deserializer.call(this, value);
            }

            if (value !== undefined) {
                attrs[attrName] = value;
            }
        }

        return attrs;
    },

    /**
     * Serialize and return object data for the purpose of saving.
     *
     * When saving to the server, the only data that will be sent in the
     * API PUT/POST call will be the data returned from toJSON().
     *
     * This will build the list based on the serializedAttrs, serializers,
     * and attrToJsonMap properties.
     *
     * Subclasses can override this to create custom serialization behavior.
     *
     * Returns:
     *     object:
     *     The serialized data.
     */
    toJSON() {
        const serializerState = {
            isNew: this.isNew(),
            loaded: this.get('loaded')
        };
        const data = {};

        for (let attrName of this.serializedAttrs) {
            const serializer = this.serializers[attrName];
            let value = this.get(attrName);

            if (serializer) {
                value = serializer.call(this, value, serializerState);
            }

            const jsonField = this.attrToJsonMap[attrName] || attrName;
            data[jsonField] = value;
        }

        if (this.supportsExtraData) {
            _.extend(data, this.extraData.toJSON());
        }

        return data;
    },

    /**
     * Handle all AJAX communication for the model and its subclasses.
     *
     * Backbone.js will internally call the model's sync function to
     * communicate with the server, which usually uses Backbone.sync.
     *
     * We wrap this to convert the data to encoded form data (instead
     * of Backbone's default JSON payload).
     *
     * We also parse the error response from Review Board so we can provide
     * a more meaningful error callback.
     *
     * Args:
     *     method (string):
     *         The HTTP method to use.
     *
     *     model (Backbone.Model):
     *         The model to sync.
     *
     *     options (object):
     *         Options for the operation.
     *
     * Option Args:
     *     data (object):
     *         Optional payload data to include.
     *
     *     form (jQuery):
     *         Optional form to be submitted.
     *
     *     attrs (Array or object):
     *         Either a list of the model attributes to sync, or a set of
     *         key/value pairs to use instead of the model attributes.
     */
    sync(method, model, options={}) {
        let data;
        let contentType;

        if (method === 'read') {
            data = options.data || {};

            const extraQueryArgs = _.result(this, 'extraQueryArgs', {});

            if (!_.isEmpty(extraQueryArgs)) {
                data = _.extend({}, extraQueryArgs, data);
            }
        } else {
            if (options.form) {
                data = null;
            } else if (options.attrs && !_.isArray(options.attrs)) {
                data = options.attrs;
            } else {
                data = model.toJSON(options);

                if (options.attrs) {
                    data = _.pick(
                        data,
                        options.attrs.map(attr => this.attrToJsonMap[attr]
                                                  || attr));
                }
            }

            contentType = 'application/x-www-form-urlencoded';
        }

        const syncOptions = _.defaults({}, options, {
            /* Use form data instead of a JSON payload. */
            contentType: contentType,
            data: data,
            processData: true
        });

        if (!options.form && this.expandedFields.length > 0) {
            syncOptions.data.expand = this.expandedFields.join(',');
        }

        syncOptions.error = xhr => {
            RB.storeAPIError(xhr);

            const rsp = xhr.errorPayload;

            if (rsp && _.has(rsp, this.rspNamespace)) {
                /*
                 * The response contains the current version of the object,
                 * which we want to preserve, in case it did any partial
                 * updating of data.
                 */
                this.set(this.parse(rsp));
            }

            if (_.isFunction(options.error)) {
                options.error(xhr);
            }
        };

        return Backbone.sync.call(this, method, model, syncOptions);
    },

    /**
     * Perform validation on the attributes of the resource.
     *
     * By default, this validates the extraData field, if provided.
     *
     * Args:
     *     attrs (object):
     *         The attributes to validate.
     *
     * Returns:
     *     string:
     *     An error string or ``undefined``.
     */
    validate(attrs) {
        if (this.supportsExtraData && attrs.extraData !== undefined) {
            const strings = RB.BaseResource.strings;

            if (!_.isObject(attrs.extraData)) {
                return strings.INVALID_EXTRADATA_TYPE;
            }

            for (let [key, value] of Object.entries(attrs.extraData)) {
                if (!_.isNull(value) &&
                    (!_.isNumber(value) || _.isNaN(value)) &&
                    !_.isBoolean(value) &&
                    !_.isString(value)) {
                    return strings.INVALID_EXTRADATA_VALUE_TYPE
                        .replace('{key}', key);
                }
            }
        }
    }
}, {
    strings: {
        UNSET_PARENT_OBJECT: 'parentObject must be set',
        INVALID_EXTRADATA_TYPE:
            'extraData must be an object or undefined',
        INVALID_EXTRADATA_VALUE_TYPE:
            'extraData.{key} must be null, a number, boolean, or string'
    }
});


_.extend(RB.BaseResource.prototype, RB.ExtraDataMixin);
