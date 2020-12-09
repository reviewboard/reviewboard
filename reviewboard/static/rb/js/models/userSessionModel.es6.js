(function() {


/**
 * An item in a StoredItems list.
 *
 * These are used internally to proxy object registration into a store list.
 * It is meant to be a temporary, internal object that can be created with
 * the proper data and then immediately saved or deleted.
 *
 * Model Attributes:
 *     baseURL (string):
 *         The root of the URL for the resource list.
 *
 *     loaded (boolean):
 *         Whether the item is loaded from the server.
 *
 *     objectID (string):
 *         The ID of the item.
 *
 *     stored (boolean):
 *         Whether or not the item has been stored on the server.
 */
const Item = RB.BaseResource.extend({
    /**
     * Return defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     Default values for the attributes.
     */
    defaults() {
        return _.defaults({
            baseURL: null,
            loaded: true,
            objectID: null,
            stored: false,
        }, RB.BaseResource.prototype.defaults());
    },

    /**
     * Return the URL for the item resource.
     *
     * Returns:
     *     string:
     *     The URL to use for updating the item.
     */
    url() {
        let url = this.get('baseURL');

        if (this.get('stored')) {
            url += this.get('objectID') + '/';
        }

        return url;
    },

    /**
     * Return whether the item is new (not yet stored on the server).
     *
     * Returns:
     *     boolean:
     *     Whether the item is new.
     */
    isNew() {
        return !this.get('stored');
    },

    /**
     * Return a JSON-serializable representation of the item.
     *
     * Returns:
     *    object:
     *    A representation of the item suitable for serializing to JSON.
     */
    toJSON() {
        return {
            object_id: this.get('objectID') || undefined,
        };
    },

    /**
     * Parse the response from the server.
     */
    parse(/* rsp */) {
    },
});


/**
 * Manages a list of stored objects.
 *
 * This interfaces with a Watched Items resource (for groups or review
 * requests) and a Hidden Items resource, allowing immediate adding/removing
 * of objects.
 *
 * Model Attributes:
 *     addError (string):
 *         The error string to use when adding an item fails.
 *
 *     removeError (string):
 *         The error string to use when removing an item fails.
 */
const StoredItems = RB.BaseResource.extend({
    /**
     * Return the defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     The default values for the model attributes.
     */
    defaults() {
        return _.defaults({
            addError: '',
            removeError: '',
        }, RB.BaseResource.prototype.defaults());
    },

    /**
     * Return the URL for the resource.
     *
     * Returns:
     *     string:
     *     The URL for the resource.
     */
    url() {
        return this.get('url');
    },

    /**
     * Immediately add an object to a stored list on the server.
     *
     * Args:
     *     obj (Item):
     *         The item to add.
     *
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to use when calling the callbacks in ``options``.
     */
    addImmediately(obj, options={}, context=null) {
        const url = this.url();

        if (url) {
            const item = new Item({
                objectID: obj.id,
                baseURL: url,
            });

            item.save(options, context);
        } else if (_.isFunction(options.error)) {
            options.error.call({
                errorText: this.addError,
            });
        }
    },

    /**
     * Immediately remove an object from a stored list on the server.
     *
     * Args:
     *     obj (Item):
     *         The item to remove.
     *
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to use when calling the callbacks in ``options``.
     */
    removeImmediately(obj, options={}, context=null) {
        const url = this.url();

        if (url) {
            const item = new Item({
                objectID: obj.id,
                baseURL: url,
                stored: true,
            });

            item.destroy(options, context);
        } else if (_.isFunction(options.error)) {
            options.error.call({
                errorText: this.removeError,
            });
        }
    },
});


/**
 * Manages the user's active session.
 *
 * This stores basic information on the user (the username and session API URL)
 * and utility objects such as the watched groups, watched review requests and
 * hidden review requests lists.
 *
 * There should only ever be one instance of a UserSession. It should always
 * be created through UserSession.create, and retrieved through
 * UserSession.instance.
 *
 * Model Attributes:
 *     archivedReviewRequestsURL (string):
 *         The URL for the archived review requests API resource.
 *
 *     authenticated (boolean):
 *         Whether the user is currently authenticated.
 *
 *     diffsShowExtraWhitespace (boolean):
 *         Whether the user wants to see diffs with excess whitespace
 *         highlighted.
 *
 *     fullName (string):
 *         The user's full name.
 *
 *     loginURL (string):
 *         The URL to the login page (if the user is anonymous).
 *
 *     mutedReviewRequestsURL (string):
 *         The URL for the archived review requests API resource.
 *
 *     readOnly (boolean):
 *         Whether the user is operating in read-only mode.
 *
 *     sessionURL (string):
 *         The URL to the session API resource.
 *
 *     timezoneOffset (string):
 *         The user's offset from UTC. This will be in the format that would
 *         attach to an ISO8601-style date, such as "-0800" for PST.
 *
 *     userFileAttachmentsURL (string):
 *         The URL for the user file attachments API resource.
 *
 *     userPageURL (string):
 *         The URL for the user's profile page.
 *
 *     username: (string):
 *         The user's username.
 *
 *     watchedReviewGroupsURL (string):
 *         The URL for the watched review groups API resource.
 *
 *     watchedReviewRequestsURL (string):
 *         The URL for the watched review requests API resource.
 */
RB.UserSession = Backbone.Model.extend({
    defaults: {
        archivedReviewRequestsURL: null,
        authenticated: false,
        diffsShowExtraWhitespace: false,
        fullName: null,
        loginURL: null,
        mutedReviewRequestsURL: null,
        readOnly: false,
        sessionURL: null,
        timezoneOffset: '0',
        userFileAttachmentsURL: null,
        userPageURL: null,
        username: null,
        watchedReviewGroupsURL: null,
        watchedReviewRequestsURL: null,
    },

    /**
     * Initialize the model.
     */
    initialize() {
        this.watchedGroups = new StoredItems({
            url: this.get('watchedReviewGroupsURL'),
            addError: gettext('Must log in to add a watched item.'),
            removeError: gettext('Must log in to remove a watched item.'),
        });

        this.watchedReviewRequests = new StoredItems({
            url: this.get('watchedReviewRequestsURL'),
            addError: gettext('Must log in to add a watched item.'),
            removeError: gettext('Must log in to remove a watched item.'),
        });

        this.archivedReviewRequests = new StoredItems({
            url: this.get('archivedReviewRequestsURL'),
            removeError: gettext('Must log in to remove a archived item.'),
            addError: gettext('Must log in to add an archived item.'),
        });

        this.mutedReviewRequests = new StoredItems({
            url: this.get('mutedReviewRequestsURL'),
            removeError: gettext('Must log in to remove a muted item.'),
            addError: gettext('Must log in to add a muted item.'),
        });

        this._bindCookie({
            attr: 'diffsShowExtraWhitespace',
            cookieName: 'show_ew',
            deserialize: value => (value !== 'false'),
        });
    },

    /**
     * Toggle a boolean attribute.
     *
     * The attribute will be the inverse of the prior value.
     *
     * Args:
     *     attr (string):
     *         The name of the attribute to toggle.
     */
    toggleAttr(attr) {
        this.set(attr, !this.get(attr));
    },

    /*
     * Return avatar HTML for the user with the given size.
     *
     * Version Added:
     *     3.0.19
     *
     * Args:
     *     size (Number):
     *         The size of the avatar, in pixels. This is both the width and
     *         height.
     *
     * Return:
     *     string:
     *     The HTML for the avatar.
     */
    getAvatarHTML: function(size) {
        var urls = this.get('avatarHTML') || {};
        return urls[size] || '';
    },

    /**
     * Return avatar URLs for the user with the given size.
     *
     * Deprecated:
     *     3.0.19:
     *     :js:meth:`getAvatarHTML` should be used instead.
     *
     * Args:
     *     size (number):
     *         The size of the avatar, in pixels. This is both the width and
     *         height.
     *
     * Return:
     *     object:
     *     An object containing avatar URLs, if the requested avatar size is
     *     available. This object will contain the following keys:
     *
     *     * ``1x``: The url for the avatar.
     *     * ``2x``: The high-DPI URL for the avatar.
     *
     *     If the requested avatar size is unavailable, this function returns
     *     an empty object.
     */
    getAvatarURLs(size) {
        const urls = this.get('avatarURLs') || {};
        return urls[size] || {};
    },

    /**
     * Bind a cookie to an attribute.
     *
     * The initial value of the attribute will be set to that of the cookie.
     *
     * When the attribute changes, the cookie will be updated.
     *
     * Args:
     *     options (object):
     *         Options for the bind.
     *
     * Option Args:
     *    attr (string):
     *        The name of the attribute to bind.
     *
     *    cookieName (string):
     *        The name of the cookie to store.
     *
     *    deserialize (function, optional):
     *        A deserialization function to use when fetching the attribute
     *        value.
     *
     *    serialize (function, optional):
     *        A serialization function to use when storing the attribute value.
     */
    _bindCookie(options) {
        const deserialize = options.deserialize || _.identity;
        const serialize = (options.serialize ||
                           (value => value.toString()));

        this.set(options.attr, deserialize($.cookie(options.cookieName)));

        this.on(`change:${options.attr}`, (model, value) => {
            $.cookie(options.cookieName, serialize(value), {
                path: SITE_ROOT,
            });
        });
    },
}, {
    instance: null,

    ARCHIVED: 'A',
    MUTED: 'M',

    /**
     * Create the UserSession for the current user.
     *
     * Only one will ever exist. Calling this a second time will assert.
     *
     * Args:
     *     options (object):
     *         Options to pass into the UserSession initializer.
     *
     * Returns:
     *     RB.UserSession:
     *     The user session instance.
     */
    create(options) {
        console.assert(!RB.UserSession.instance,
                       'UserSession.create can only be called once.');

        RB.UserSession.instance = new RB.UserSession(options);
        return RB.UserSession.instance;
    },
});


})();
