/*
 * An item in a WatchedItems list.
 *
 * These are used internally to proxy object registration into a watch list.
 * It is meant to be a temporary, internal object that can be created with
 * the proper data and then immediately saved or deleted.
 */
var Item = RB.BaseResource.extend({
    defaults: _.defaults({
        objectID: null,
        baseURL: null,
        watched: false,
        loaded: true
    }, RB.BaseResource.prototype.defaults),

    url: function() {
        var url = this.get('baseURL');

        if (this.get('watched')) {
            url += this.get('objectID') + '/';
        }

        return url;
    },

    isNew: function() {
        return !this.get('watched');
    },

    toJSON: function() {
        return {
            object_id: this.get('objectID') || undefined
        };
    },

    parse: function(/* rsp */) {
    }
});


/*
 * Manages a list of watched objects.
 *
 * This interfaces with a Watched Items resource (for groups or review
 * requests) and allows immediate adding/removing of objects.
 */
var WatchedItems = RB.BaseResource.extend({
    url: function() {
        return this.get('url');
    },

    /*
     * Immediately adds an object to a watched list on the server.
     */
    addImmediately: function(obj, options, context) {
        var url = this.url(),
            item;

        if (url) {
            item = new Item({
                objectID: obj.id,
                baseURL: url
            });

            item.save(options, context);
        } else if (options && _.isFunction(options.error)) {
            options.error.call({
                errorText: 'Must log in to add a watched item.'
            });
        }
    },

    /*
     * Immediately removes an object from a watched list on the server.
     */
    removeImmediately: function(obj, options, context) {
        var url = this.url(),
            item;

        if (url) {
            item = new Item({
                objectID: obj.id,
                baseURL: url,
                watched: true
            });

            item.destroy(options, context);
        } else if (options && _.isFunction(options.error)) {
            options.error.call({
                errorText: 'Must log in to add a watched item.'
            });
        }
    }
});


/*
 * Manages the user's active session.
 *
 * This stores basic information on the user (the username and session API URL)
 * and utility objects such as the watched groups and review requests lists.
 *
 * There should only ever be one instance of a UserSession. It should always
 * be created through UserSession.create, and retrieved through
 * UserSession.instance.
 */
RB.UserSession = Backbone.Model.extend({
    defaults: {
        authenticated: false,
        diffsShowExtraWhitespace: false,
        fullName: null,
        loginURL: null,
        username: null,
        userPageURL: null,
        sessionURL: null,
        timezoneOffset: '0',
        watchedReviewGroupsURL: null,
        watchedReviewRequestsURL: null
    },

    initialize: function() {
        this.watchedGroups = new WatchedItems({
            url: this.get('watchedReviewGroupsURL')
        });

        this.watchedReviewRequests = new WatchedItems({
            url: this.get('watchedReviewRequestsURL')
        });

        this._bindCookie({
            attr: 'diffsShowExtraWhitespace',
            cookieName: 'show_ew',
            deserialize: function(value) {
                return value !== 'false';
            }
        });
    },

    /*
     * Toggles a boolean attribute.
     *
     * The attribute will be the inverse of the prior value.
     */
    toggleAttr: function(attr) {
        this.set(attr, !this.get(attr));
    },

    /*
     * Binds a cookie to an attribute.
     *
     * The initial value of the attribute will be set to that of the cookie.
     *
     * When the attribute changes, the cookie will be updated.
     */
    _bindCookie: function(options) {
        var deserialize = options.deserialize || _.identity,
            serialize = options.serialize || function(value) {
                return value.toString();
            };

        this.set(options.attr, deserialize($.cookie(options.cookieName)));

        this.on('change:' + options.attr, function(model, value) {
            $.cookie(options.cookieName, serialize(value), {
                path: SITE_ROOT
            });
        }, this);
    }
}, {
    instance: null,

    /*
     * Creates the UserSession for the current user.
     *
     * Only one will ever exist. Calling this a second time will assert.
     */
    create: function(options) {
        console.assert(!RB.UserSession.instance,
                       "UserSession.create can only be called once.");

        RB.UserSession.instance = new RB.UserSession(options);
        return RB.UserSession.instance;
    }
});
