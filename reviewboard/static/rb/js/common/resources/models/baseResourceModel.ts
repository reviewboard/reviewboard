/**
 * The base model for all API-based resource models.
 */
import { BaseModel, ModelAttributes, spina } from '@beanbag/spina';

import { ExtraDataMixin } from '../../models/extraDataMixin';
import { SerializerState } from '../utils/serializers';


/** A link within the resource tree. */
export interface ResourceLink {
    /** The link URL. */
    href: string;

    /** The HTTP method to use. */
    method?: string;

    /** The title for the link. */
    title?: string;
}


/**
 * Attributes for the BaseResource model.
 *
 * Version Added:
 *     6.0
 */
export interface BaseResourceAttrs extends ModelAttributes {
    /** Extra data storage. */
    extraData: object;

    /** The resource links. */
    links: {
        [key: string]: ResourceLink;
    };

    /** Whether the resource has been loaded from the server. */
    loaded: boolean;

    /** The parent object. */
    parentObject: BaseResource;
}


/**
 * Options for the ready operation.
 *
 * Version Added:
 *     6.0
 */
export interface ReadyOptions extends Backbone.PersistenceOptions {
    /** Data to send when fetching the object from the server. */
    data?: object;

    /**
     * A callback function to call when the object is ready.
     *
     * This is deprecated, and new code should be written to use the promise
     * return value from the ready method.
     */
    ready?: (() => void) | undefined;
}


/**
 * Options for the save operation.
 *
 * Version Added:
 *     6.0
 */
export interface SaveOptions extends Backbone.ModelSaveOptions {
    /** Additional attributes to include in the payload. */
    attrs?: {
        [key: string]: unknown;
    };
}


/**
 * Options for saving the resource with files.
 *
 * Version Added:
 *     6.0
 */
interface SaveWithFilesOptions extends SaveOptions {
    /** The boundary to use when formatting multipart payloads. */
    boundary?: string;
}


interface SyncOptions extends JQuery.AjaxSettings {
    /**
     * Attributes to sync.
     *
     * This is either a list of model attribute names to sync, or a set of
     * key/value pairs to use instead of the model attributes.
     */
    attrs?: string[] | { [key: string]: unknown; };

    /** Optional payload data to include. */
    data?: object;

    /** Optional form to be submitted. */
    form?: JQuery;
}


type SerializerMap = {
    [key: string]: (unknown, SerializerState) => unknown,
}


type DeserializerMap = {
    [key: string]: (unknown) => unknown,
}


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
@spina({
    mixins: [ExtraDataMixin],
    prototypeAttrs: [
        'attrToJsonMap',
        'deserializedAttrs',
        'deserializers',
        'expandedFields',
        'extraQueryArgs',
        'rspNamespace',
        'serializedAttrs',
        'serializers',
        'supportsExtraData',
        'urlIDAttr',
    ],
})
export class BaseResource<
    TDefaults extends BaseResourceAttrs = BaseResourceAttrs
> extends BaseModel<TDefaults> {
    static strings = {
        INVALID_EXTRADATA_TYPE:
            'extraData must be an object or undefined',
        INVALID_EXTRADATA_VALUE_TYPE:
            'extraData.{key} must be null, a number, boolean, or string',
        UNSET_PARENT_OBJECT: 'parentObject must be set',
    };

    /** The key for the namespace for the object's payload in a response. */
    static rspNamespace = '';

    /** The attribute used for the ID in the URL. */
    static urlIDAttr = 'id';

    /** The list of fields to expand in resource payloads. */
    static expandedFields: string[] = [];

    /**
     * Extra query arguments for GET requests.
     *
     * This may also be a function that returns the extra query arguments.
     *
     * These values can be overridden by the caller when making a request.
     * They function as defaults for the queries.
     */
    static extraQueryArgs = {};

    /** Whether or not extra data can be associated on the resource. */
    static supportsExtraData = false;

    /**
     * A map of attribute names to resulting JSON field names.
     *
     * This is used to auto-generate a JSON payload from attribute names
     * in toJSON().
     *
     * It's also needed if using attribute names in any save({attrs: [...]})
     * calls.
     */
    static attrToJsonMap = {};

    /** A list of attributes to serialize in toJSON(). */
    static serializedAttrs: string[] = [];

    /** A list of attributes to deserialize in parseResourceData(). */
    static deserializedAttrs: string[] = [];

    /** Special serializer functions called in toJSON(). */
    static serializers: SerializerMap = {};

    /** Special deserializer functions called in parseResourceData(). */
    static deserializers: DeserializerMap = {};

    /**
     * Return default values for the model attributes.
     *
     * Returns:
     *     object:
     *     The attribute defaults.
     */
    defaults(): BaseResourceAttrs {
        return {
            extraData: {},
            links: null,
            loaded: false,
            parentObject: null,
        };
    }

    /**
     * Return the key to use when accessing the list resource.
     *
     * Returns:
     *     string:
     *     The name of the key to use when loading data from the list resource.
     */
    listKey() {
        return this.rspNamespace + 's';
    }

    /**
     * Initialize the model.
     */
    initialize() {
        if (this.supportsExtraData) {
            this._setupExtraData();
        }
    }

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
    url(): string {
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
    }

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
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
     *
     * Args:
     *     options (ReadyOptions):
     *         Options for the fetch operation.
     *
     *     context (object):
     *         Context to bind when executing callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async ready(
        options: ReadyOptions = {},
        context: object = undefined,
    ): Promise<void> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete) ||
            _.isFunction(options.ready)) {
            console.warn('BaseResource.ready was called using callbacks. ' +
                         'Callers should be updated to use promises instead.');

            return RB.promiseToCallbacks(
                options, context, () => this.ready());
        }

        const parentObject = this.get('parentObject');

        if (!this.get('loaded')) {
            if (!this.isNew()) {
                // Fetch data from the server
                await this.fetch({ data: options.data });
            } else if (parentObject) {
                /*
                 * This is a new object, which means there's nothing to fetch
                 * from the server, but we still need to ensure that the
                 * parent is loaded in order for it to have valid links.
                 */
                await parentObject.ready();
            }
        }
    }

    /**
     * Call a function when we know an object exists server-side.
     *
     * This works like ready() in that it's used to delay operating on the
     * resource until we have a server-side representation. Unlike ready(),
     * it will attempt to create it if it doesn't exist first.
     *
     * If we fail to create the object, options.error() will be called
     * instead.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Object with success and error callbacks.
     *
     *     context (object, optional):
     *         Context to bind when executing callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async ensureCreated(
        options: Backbone.PersistenceOptions = {},
        context: object = undefined,
    ): Promise<void> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('BaseResource.ensureCreated was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');

            return RB.promiseToCallbacks(
                options, context, () => this.ensureCreated());
        }

        await this.ready();

        if (!this.get('loaded')) {
            await(this.save());
        }
    }

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
     * Version Changed:
     *     5.0:
     *     Deprecated the callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Options to pass through to the base Backbone fetch operation.
     *
     *     context (object, optional):
     *         Context to bind when executing callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async fetch(
        options: Backbone.ModelFetchOptions = {},
        context: object = undefined,
    ): Promise<void> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('BaseResource.fetch was called using callbacks. ' +
                         'Callers should be updated to use promises instead.');

            return RB.promiseToCallbacks(
                options, context, newOptions => this.fetch(newOptions));
        }

        if (this.isNew()) {
            throw new Error(
                'fetch cannot be used on a resource without an ID');
        }

        const parentObject = this.get('parentObject');

        if (parentObject) {
            await parentObject.ready();
        }

        return new Promise((resolve, reject) => {
            super.fetch(_.extend({
                error: (model, xhr, options) => reject(
                    new BackboneError(model, xhr, options)),
                success: () => resolve(),
            }, options));
        });
    }

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
     * Version Changed:
     *     5.0:
     *     Deprecated the callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when executing callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async save(
        options: SaveOptions = {},
        context: object = undefined,
    ): Promise<JQuery.jqXHR> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('BaseResource.save was called using callbacks. ' +
                         'Callers should be updated to use promises instead.');

            return RB.promiseToCallbacks(
                options, context, newOptions => this.save(newOptions));
        }

        this.trigger('saving', options);
        await this.ready();

        const parentObject = this.get('parentObject');

        if (parentObject) {
            await parentObject.ensureCreated();
        }

        return this._saveObject(options);
    }

    /**
     * Handle the actual saving of the object's state.
     *
     * This is called internally by save() once we've handled all the
     * readiness and creation checks of this object and its parent.
     *
     * Args:
     *     options (object):
     *         Options for the save operation.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    _saveObject(
        options: Backbone.ModelSaveOptions,
    ): Promise<JQuery.jqXHR> {
        return new Promise((resolve, reject) => {
            const url = _.result(this, 'url');

            if (!url) {
                reject(new Error(
                    'The object must either be loaded from the server or ' +
                    'have a parent object before it can be saved'));

                return;
            }

            const saveOptions = _.defaults({
                error: (model, xhr, options) => {
                    this.trigger('saveFailed', options);
                    reject(new BackboneError(model, xhr, options));
                },
                success: (model, xhr) => {
                    this.trigger('saved', options);
                    resolve(xhr);
                },
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
                        const ready = readers.every(
                            r => (r.readyState === FileReader.DONE));

                        if (ready) {
                            this._saveWithFiles(files, readers, saveOptions);
                        }
                    };

                    reader.readAsArrayBuffer(file);
                });
            } else {
                super.save({}, saveOptions);
            }
        });
    }

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
     *     options (SaveWithFilesOptions):
     *         Options for the save operation.
     */
    _saveWithFiles(
        files,
        fileReaders: FileReader[],
        options: SaveWithFilesOptions,
    ) {
        const boundary = options.boundary ||
                         ('-----multipartformboundary' + new Date().getTime());
        const blob = [];

        for (const [key, file, reader] of
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

        for (const [key, value] of Object.entries(options.attrs)) {
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

        super.save({}, _.extend({
            contentType: 'multipart/form-data; boundary=' + boundary,
            data: new Blob(blob),
            processData: false,
        }, options));
    }

    /**
     * Delete the object's resource on the server.
     *
     * An object must either be loaded or have a parent resource linking to
     * this object's list resource URL for an object to be deleted.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and changed to return a promise.
     *
     * Args:
     *     options (object, optional):
     *         Object with success and error callbacks.
     *
     *     context (object, optional):
     *         Context to use when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async destroy(
        options: Backbone.ModelDestroyOptions = {},
        context: object = undefined,
    ): Promise<void> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('BaseResource.destroy was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');

            return RB.promiseToCallbacks(
                options, context, newOptions => this.destroy(newOptions));
        }

        this.trigger('destroying', options);

        const parentObject = this.get('parentObject');

        if (!this.isNew() && parentObject) {
            /*
             * XXX This is temporary to support older-style resource
             *     objects. We should just use ready() once we're moved
             *     entirely onto BaseResource.
             */
            await parentObject.ready();
        }

        await this._destroyObject(options);
    }

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
     *         Options object to include with events.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    async _destroyObject(
        options: Backbone.ModelDestroyOptions = {},
    ): Promise<void> {
        const url = _.result(this, 'url');

        if (url) {
            await this.ready();
            await this._finishDestroy(options);
        } else {
            if (this.isNew()) {
                /*
                 * If both this resource and its parent are new, it's
                 * possible that we'll get through here without a url. In
                 * this case, all the data is still local to the client
                 * and there's not much to clean up; just call
                 * Model.destroy and be done with it.
                 */
                await this._finishDestroy(options);
            } else {
                throw new Error(
                    'The object must either be loaded from the server ' +
                    'or have a parent object before it can be deleted'
                );
            }
        }
    }

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
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    _finishDestroy(
        options: Backbone.ModelDestroyOptions,
    ): Promise<void> {
        return new Promise((resolve, reject) => {
            const parentObject = this.get('parentObject');

            super.destroy({
                error: (model, xhr, options) => reject(
                    new BackboneError(model, xhr, options)),
                success: () => {
                    /*
                     * Reset the object so it's new again, but with the same
                     * parentObject.
                     */
                    this.set(_.defaults(
                        {
                            id: null,
                            parentObject: parentObject,
                        },
                        _.result(this, 'defaults')));

                    this.trigger('destroyed', options);

                    resolve();
                },
                wait: true,
            });
        });
    }

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
    parse(
        rsp: object,
    ): TDefaults {
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
    }

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
    parseResourceData(
        rsp: object,
    ): Partial<TDefaults> {
        const attrs = {};

        for (const attrName of this.deserializedAttrs) {
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
    }

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
     * Args:
     *     options (object):
     *         Options for the save operation.
     *
     * Returns:
     *     object:
     *     The serialized data.
     */
    toJSON(
        options?: object,
    ): object {
        const serializerState: SerializerState = {
            isNew: this.isNew(),
            loaded: this.get('loaded'),
        };
        const data = {};

        for (const attrName of this.serializedAttrs) {
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
    }

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
     *     options (SyncOptions):
     *         Options for the operation.
     */
    sync(
        method: string,
        model: Backbone.Model,
        options: SyncOptions = {},
    ) {
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
            processData: true,
        });

        if (!options.form && this.expandedFields.length > 0) {
            syncOptions.data.expand = this.expandedFields.join(',');
        }

        syncOptions.error = (xhr, textStatus, jqXHR) => {
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
                options.error(xhr, textStatus, jqXHR);
            }
        };

        return Backbone.sync.call(this, method, model, syncOptions);
    }

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
    validate(
        attrs: TDefaults,
    ): string | undefined {
        if (this.supportsExtraData && attrs.extraData !== undefined) {
            const strings = BaseResource.strings;

            if (!_.isObject(attrs.extraData)) {
                return strings.INVALID_EXTRADATA_TYPE;
            }

            for (const [key, value] of Object.entries(attrs.extraData)) {
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
