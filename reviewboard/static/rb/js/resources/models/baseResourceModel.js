/*
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
    defaults: function() {
        return {
            extraData: {},
            links: null,
            loaded: false,
            parentObject: null
        };
    },

    /* The key for the namespace for the object's payload in a response. */
    rspNamespace: '',

    /* The attribute used for the ID in the URL. */
    urlIDAttr: 'id',

    listKey: function() {
        return this.rspNamespace + 's';
    },

    /* The list of fields to expand in resource payloads. */
    expandedFields: [],

    /*
     * Extra query arguments for GET requests.
     *
     * This may also be a function that returns the extra query arguments.
     *
     * These values can be overridden by the caller when making a request.
     * They function as defaults for the queries.
     */
    extraQueryArgs: {},

    /* Whether or not extra data can be associated on the resource. */
    supportsExtraData: false,

    /*
     * A map of attribute names to resulting JSON field names.
     *
     * This is used to auto-generate a JSON payload from attribute names
     * in toJSON().
     *
     * It's also needed if using attribute names in any save({attrs: [...]})
     * calls.
     */
    attrToJsonMap: {},

    /* A list of attributes to serialize in toJSON(). */
    serializedAttrs: [],

    /* A list of attributes to deserialize in parseResourceData(). */
    deserializedAttrs: [],

    /* Special serializer functions called in toJSON(). */
    serializers: {},

    /* Special deserializer functions called in parseResourceData(). */
    deserializers: {},

    /*
     * Returns the URL for this resource's instance.
     *
     * If this resource is loaded and has a URL to itself, that URL will
     * be returned.
     *
     * If not yet loaded, it'll try to get it from its parent object, if
     * any.
     *
     * This will return null if we can't auto-determine the URL.
     */
    url: function() {
        var links = this.get('links'),
            baseURL,
            key,
            link,
            parentObject;

        if (links) {
            return links.self.href;
        } else {
            parentObject = this.get('parentObject');

            if (parentObject) {
                links = parentObject.get('links');

                if (links) {
                    key = _.result(this, 'listKey');
                    link = links[key];

                    if (link) {
                        baseURL = link.href;

                        return this.isNew()
                               ? baseURL
                               : (baseURL + this.get(this.urlIDAttr) + '/');
                    }
                }
            }
        }

        return null;
    },

    /*
     * Calls a function when the object is ready to use.
     *
     * An object is ready it has an ID and is loaded, or is a new resource.
     *
     * When the object is ready, options.ready() will be called. This may
     * be called immediately, or after one or more round trips to the server.
     *
     * If we fail to load the resource, objects.error() will be called instead.
     */
    ready: function(options, context) {
        var parentObject = this.get('parentObject'),
            success,
            error;

        options = options || {};

        success = options.ready ? _.bind(options.ready, context)
                                : undefined;
        error = options.error ? _.bind(options.error, context)
                              : undefined;

        if (this.get('loaded')) {
            // We already have data--just call the callbacks
            if (options.ready) {
                options.ready.call(context);
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
        } else if (options.ready) {
            // Fallback for dummy objects
            options.ready.call(context);
        }
    },

    /*
     * Calls a function when we know an object exists server-side.
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
     */
    ensureCreated: function(options, context) {
        options = options || {};

        this.ready({
            ready: function() {
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
        }, this);
    },

    /*
     * Fetches the object's data from the server.
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
     */
    fetch: function(options, context) {
        var parentObject,
            fetchObject;

        options = options || {};

        if (this.isNew()) {
            if (_.isFunction(options.error)) {
                options.error.call(context,
                    'fetch cannot be used on a resource without an ID');
            }

            return;
        }

        parentObject = this.get('parentObject');
        fetchObject = _.bind(Backbone.Model.prototype.fetch, this,
                             _.bindCallbacks(options, context));

        if (parentObject) {
            parentObject.ready({
                ready: fetchObject,
                error: options.error
            }, this);
        } else {
            fetchObject();
        }
    },

    /*
     * Saves the object's data to the server.
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
     */
    save: function(options, context) {
        options = options || {};

        this.trigger('saving', options);

        this.ready({
            ready: function() {
                var parentObject = this.get('parentObject');

                if (parentObject) {
                    parentObject.ensureCreated({
                        success: _.bind(this._saveObject, this, options,
                                        context),
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

    /*
     * Handles the actual saving of the object's state.
     *
     * This is called internally by save() once we've handled all the
     * readiness and creation checks of this object and its parent.
     */
    _saveObject: function(options, context) {
        var url = _.result(this, 'url'),
            files = [],
            readers = [],
            saveOptions;

        if (!url) {
            if (_.isFunction(options.error)) {
                options.error.call(context,
                    'The object must either be loaded from the server or ' +
                    'have a parent object before it can be saved');
            }

            return;
        }

        saveOptions = _.defaults({
            success: _.bind(function() {
                if (_.isFunction(options.success)) {
                    options.success.apply(context, arguments);
                }

                this.trigger('saved', options);
            }, this),

            error: _.bind(function() {
                if (_.isFunction(options.error)) {
                    options.error.apply(context, arguments);
                }

                this.trigger('saveFailed', options);
            }, this)
        }, options);

        saveOptions.attrs = options.attrs || this.toJSON(options);

        if (!options.form) {
            if (this.payloadFileKeys && window.File) {
                /* See if there are files in the attributes we're using. */
                _.each(this.payloadFileKeys, function(key) {
                    var file = saveOptions.attrs[key];
                    if (file) {
                        files.push(file);
                    }
                });
            }
        }

        if (files.length > 0) {
            _.each(files, function(file) {
                var reader = new FileReader(),
                    testDone = function(reader) {
                        return reader.readyState === FileReader.DONE;
                    };

                readers.push(reader);
                reader.onloadend = _.bind(function() {
                    if (_.every(readers, testDone)) {
                        this._saveWithFiles(files, readers, saveOptions);
                    }
                }, this);
                reader.readAsArrayBuffer(file);
            }, this);
        } else {
            Backbone.Model.prototype.save.call(this, {}, saveOptions);
        }
    },

    /*
     * Saves the model with a file upload.
     *
     * When doing file uploads, we need to hand-structure a form-data payload
     * to the server. It will contain the file contents and the attributes
     * we're saving. We can then call the standard save function with this
     * payload as our data.
     */
    _saveWithFiles: function(files, fileReaders, options) {
        var boundary = options.boundary ||
                       ('-----multipartformboundary' + new Date().getTime()),
            blob = [];

        _.each(_.zip(this.payloadFileKeys, files, fileReaders), function(data) {
            var key = data[0],
                file = data[1],
                reader = data[2],
                fileBlobLen,
                fileBlob,
                i;

            if (!file || !reader) {
                return;
            }

            blob.push('--' + boundary + '\r\n');
            blob.push('Content-Disposition: form-data; name="' +
                      key + '"; filename="' + file.name + '"\r\n');
            blob.push('Content-Type: ' + file.type + '\r\n');
            blob.push('\r\n');

            fileBlob = new Uint8Array(reader.result);
            fileBlobLen = fileBlob.length;

            for (i = 0; i < fileBlobLen; i++) {
                blob.push(String.fromCharCode(fileBlob[i]));
            }

            blob.push('\r\n');
        });

        _.each(options.attrs, function(value, key) {
            if (   !_.contains(this.payloadFileKeys, key)
                && value !== undefined
                && value !== null) {
                blob.push('--' + boundary + '\r\n');
                blob.push('Content-Disposition: form-data; name="' + key +
                          '"\r\n');
                blob.push('\r\n');
                blob.push(value + '\r\n');
            }
        }, this);

        blob.push('--' + boundary + '--\r\n\r\n');

        Backbone.Model.prototype.save.call(this, {}, _.extend({
            data: blob.join(''),
            processData: false,
            contentType: 'multipart/form-data; boundary=' + boundary,
            xhr: this._binaryXHR
        }, options));
    },

    /*
     * Builds a binary-capable XHR.
     *
     * Since we must send files as blob data, and not all XHR implementations
     * do this by default, we must override the XHR and change which send
     * function it will use.
     */
    _binaryXHR: function() {
        var xhr = $.ajaxSettings.xhr();

        xhr.send = xhr.sendAsBinary;

        return xhr;
    },

    /*
     * Deletes the object's resource on the server.
     *
     * An object must either be loaded or have a parent resource linking to
     * this object's list resource URL for an object to be deleted.
     *
     * If we successfully delete the resource, options.success() will be
     * called.
     *
     * If we fail to delete the resource, options.error() will be called.
     */
    destroy: function(options, context) {
        var parentObject = this.get('parentObject'),
            destroyObject = _.bind(this._destroyObject,
                                   this, options, context);

        this.trigger('destroying', options);

        if (!this.isNew() && parentObject) {
            /*
             * XXX This is temporary to support older-style resource
             *     objects. We should just use ready() once we're moved
             *     entirely onto BaseResource.
             */
            parentObject.ready(_.defaults({
                ready: destroyObject
            }, _.bindCallbacks(options, context)));
        } else {
            destroyObject();
        }
    },

    /*
     * Sets up the deletion of the object.
     *
     * This is called internally by destroy() once we've handled all the
     * readiness and creation checks of this object and its parent.
     *
     * Once we've done some work to ensure the URL is valid and the object
     * is ready, we'll finish destruction by calling _finishDestroy.
     */
    _destroyObject: function(options, context) {
        var url = _.result(this, 'url');

        options = options || {};

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
            ready: function() {
                this._finishDestroy(options, context);
            },
            error: _.isFunction(options.error)
                   ? _.bind(options.error, context)
                   : undefined
        }, this);
    },

    /*
     * Finishes destruction of the object.
     *
     * This will call the parent destroy method, then reset the state
     * of the object on success.
     */
    _finishDestroy: function(options, context) {
        var self = this,
            parentObject = this.get('parentObject');

        Backbone.Model.prototype.destroy.call(this, _.defaults({
            wait: true,
            success: function() {
                /*
                 * Reset the object so it's new again, but with the same
                 * parentObject.
                 */
                self.set(_.result(self, 'defaults'));
                self.set({
                    id: null,
                    parentObject: parentObject
                });

                self.trigger('destroyed', options);

                if (_.isFunction(options.success)) {
                    options.success.apply(context, arguments);
                }
            }
        }, _.bindCallbacks(options, context)));
    },

    /*
     * Parses and returns the payload from an API response.
     *
     * This will by default only return the object's ID and list of links.
     * Subclasses should override this to return any additional data that's
     * needed, but they must include the results of
     * BaseResource.protoype.parse as well.
     */
    parse: function(rsp) {
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
     * Parses the resource data from a payload.
     *
     * By default, this will make use of attrToJsonMap and any
     * jsonDeserializers to construct a resulting set of attributes.
     *
     * This can be overridden by subclasses.
     */
    parseResourceData: function(rsp) {
        var len = this.deserializedAttrs.length,
            attrs = {},
            attrName,
            jsonField,
            value,
            i;

        for (i = 0; i < len; i++) {
            attrName = this.deserializedAttrs[i];
            deserializer = this.deserializers[attrName];
            jsonField = this.attrToJsonMap[attrName] || attrName;
            value = rsp[jsonField];

            if (deserializer) {
                value = deserializer.call(this, value);
            }

            if (value !== undefined) {
                attrs[attrName] = value;
            }
        }

        return attrs;
    },

    /*
     * Serializes and returns object data for the purpose of saving.
     *
     * When saving to the server, the only data that will be sent in the
     * API PUT/POST call will be the data returned from toJSON().
     *
     * This will build the list based on the serializedAttrs, serializers,
     * and attrToJsonMap properties.
     *
     * Subclasses can override this to create custom serialization behavior.
     */
    toJSON: function() {
        var serializerState = {
                isNew: this.isNew(),
                loaded: this.get('loaded')
            },
            len = this.serializedAttrs.length,
            data = {},
            attrName,
            jsonField,
            value,
            i;

        for (i = 0; i < len; i++) {
            attrName = this.serializedAttrs[i];
            serializer = this.serializers[attrName];
            value = this.get(attrName);

            if (serializer) {
                value = serializer.call(this, value, serializerState);
            }

            jsonField = this.attrToJsonMap[attrName] || attrName;
            data[jsonField] = value;
        }

        if (this.supportsExtraData) {
            _.each(this.get('extraData'), function(value, key) {
                data['extra_data.' + key] = value;
            }, this);
        }

        return data;
    },

    /*
     * Handles all AJAX communication for the model and its subclasses.
     *
     * Backbone.js will internally call the model's sync function to
     * communicate with the server, which usually uses Backbone.sync.
     *
     * We wrap this to convert the data to encoded form data (instead
     * of Backbone's default JSON payload).
     *
     * We also parse the error response from Review Board so we can provide
     * a more meaningful error callback.
     */
    sync: function(method, model, options) {
        var data,
            contentType,
            extraQueryArgs,
            syncOptions;

        options = options || {};

        if (method === 'read') {
            data = options.data || {};

            extraQueryArgs = _.result(this, 'extraQueryArgs', {});

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
                    data = _.pick(data, _.map(options.attrs, function(attr) {
                        return this.attrToJsonMap[attr] || attr;
                    }, this));
                }
            }

            contentType = 'application/x-www-form-urlencoded';
        }

        syncOptions = _.defaults({}, options, {
            /* Use form data instead of a JSON payload. */
            contentType: contentType,
            data: data,
            processData: true
        });

        if (!options.form && this.expandedFields.length > 0) {
            syncOptions.data.expand = this.expandedFields.join(',');
        }

        syncOptions.error = _.bind(function(xhr) {
            var rsp;

            RB.storeAPIError(xhr);

            rsp = xhr.errorPayload;

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
        }, this);

        return Backbone.sync.call(this, method, model, syncOptions);
    },

    /*
     * Performs validation on the attributes of the resource.
     *
     * By default, this validates the extraData field, if provided.
     */
    validate: function(attrs) {
        var strings = RB.BaseResource.strings,
            value,
            key;

        if (this.supportsExtraData && attrs.extraData !== undefined) {
            if (!_.isObject(attrs.extraData)) {
                return strings.INVALID_EXTRADATA_TYPE;
            }

            for (key in attrs.extraData) {
                if (attrs.extraData.hasOwnProperty(key)) {
                    value = attrs.extraData[key];

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
    }
}, {
    strings: {
        UNSET_PARENT_OBJECT: 'parentObject must be set',
        INVALID_EXTRADATA_TYPE:
            'extraData must be an object, null, or undefined',
        INVALID_EXTRADATA_VALUE_TYPE:
            'extraData.{key} must be null, a number, boolean, or string'
    }
});
