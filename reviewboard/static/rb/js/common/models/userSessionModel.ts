/**
 * Object to manage the user's session.
 */
import { BaseModel, ModelAttributes, spina } from '@beanbag/spina';

import {
    BaseResource,
    BaseResourceAttrs,
} from '../resources/models/baseResourceModel';


declare const SITE_ROOT: string;


/** Attributes for the StoredItems model. */
interface StoredItemsAttrs extends BaseResourceAttrs {
    /** The root of the URL for the resource list. */
    baseURL: string;

    /** The ID of the item. */
    objectID: string;

    /** Whether or not the item has been stored on the server. */
    stored: boolean;
}


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
@spina
class Item extends BaseResource<StoredItemsAttrs> {
    /**
     * Return defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     Default values for the attributes.
     */
    defaults(): StoredItemsAttrs {
        return _.defaults({
            baseURL: null,
            loaded: true,
            objectID: null,
            stored: false,
        }, super.defaults());
    }

    /**
     * Return the URL for the item resource.
     *
     * Returns:
     *     string:
     *     The URL to use for updating the item.
     */
    url(): string {
        let url = this.get('baseURL');

        if (this.get('stored')) {
            url += this.get('objectID') + '/';
        }

        return url;
    }

    /**
     * Return whether the item is new (not yet stored on the server).
     *
     * Returns:
     *     boolean:
     *     Whether the item is new.
     */
    isNew(): boolean {
        return !this.get('stored');
    }

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
    }

    /**
     * Parse the response from the server.
     */
    parse(/* rsp */): StoredItemsAttrs {
        return undefined;
    }
}


/** Attributes for the StoredItems model. */
interface StoredItemsAttrs extends BaseResourceAttrs {
    /** The error to use when adding an item fails. */
    addError: string;

    /** The error to use when removing an item fails. */
    removeError: string;
}


/**
 * Manages a list of stored objects.
 *
 * This interfaces with a Watched Items resource (for groups or review
 * requests) and a Hidden Items resource, allowing immediate adding/removing
 * of objects.
 */
@spina
class StoredItems extends BaseResource<StoredItemsAttrs> {
    /**
     * Return the defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     The default values for the model attributes.
     */
    defaults(): StoredItemsAttrs {
        return _.defaults({
            addError: '',
            removeError: '',
        }, super.defaults());
    }

    /**
     * Return the URL for the resource.
     *
     * Returns:
     *     string:
     *     The URL for the resource.
     */
    url() {
        return this.get('url');
    }

    /**
     * Immediately add an object to a stored list on the server.
     *
     * Version Changed:
     *     6.0:
     *     Removed options and context parameters.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated the options and context parameters and changed to return
     *     a promise.
     *
     * Args:
     *     obj (Backbone.Model):
     *         The item to add.
     *
     *     options (object, optional):
     *         Options for the save operation.
     *
     *     context (object, optional):
     *         Context to use when calling the callbacks in ``options``.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    addImmediately(obj: Backbone.Model) {
        const url = this.url();

        if (url) {
            const item = new Item({
                baseURL: url,
                objectID: String(obj.id),
            });

            return item.save();
        } else {
            return Promise.reject(new Error(this.attributes.addError));
        }
    }

    /**
     * Immediately remove an object from a stored list on the server.
     *
     * Version Changed:
     *     6.0:
     *     Removed options and context parameters.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated the options and context parameters and changed to return
     *     a promise.
     *
     * Args:
     *     obj (Backbone.Model):
     *         The item to remove.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    removeImmediately(obj: Backbone.Model) {
        const url = this.url();

        return new Promise((resolve, reject) => {
            if (url) {
                const item = new Item({
                    baseURL: url,
                    objectID: String(obj.id),
                    stored: true,
                });

                resolve(item.destroy());
            } else {
                reject(new Error(this.attributes.removeError));
            }
        });
    }
}


/** Attributes for the UserSession model. */
interface UserSessionAttrs extends ModelAttributes {
    /** The URL for the archived review requests API resource. */
    archivedReviewRequestsURL: string;

    /** Whether the user is currently authenticated. */
    authenticated: boolean;

    /**
     * Whether the user wants to see diffs with excess whitespace highlighted.
     */
    diffsShowExtraWhitespace: boolean;

    /** The user's full name. */
    fullName: string;

    /** The URL to the login page (if the user is anonymous). */
    loginURL: string;

    /** The URL for the muted review requests API resource. */
    mutedReviewRequestsURL: string;

    /** Whether the server is operating in read-only mode. */
    readOnly: boolean;

    /** The URL to the session API resource. */
    sessionURL: string;

    /** Whether to show the "Tips" box in the review dialog. */
    showReviewDialogTips: boolean;

    /**
     * The user's offset from UTC.
     *
     * This should be in the format that will attach to an ISO 8601 style date,
     * such as "-0800" for PST.
     */
    timezoneOffset: string;

    /** The URL for the user file attachments API resource. */
    userFileAttachmentsURL: string;

    /** The URL for the user's profile page. */
    userPageURL: string;

    /** The user's username. */
    username: string;

    /** The URL for the watched review groups API resource. */
    watchedReviewGroupsURL: string;

    /** The URL for the watched review requests API resource. */
    watchedReviewRequestsURL: string;
}


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
 */
@spina
export class UserSession extends BaseModel<UserSessionAttrs> {
    /** The singleton instance of the session object. */
    static instance: UserSession = null;

    /**
     * Create the UserSession for the current user.
     *
     * Only one will ever exist. Calling this a second time will assert.
     *
     * Args:
     *     attributes (object):
     *         Attributes to pass into the UserSession initializer.
     *
     * Returns:
     *     UserSession:
     *     The user session instance.
     */
    static create(
        attributes: Partial<UserSessionAttrs>,
    ): UserSession {
        console.assert(!this.instance,
                       'UserSession.create can only be called once.');

        this.instance = new this(attributes);

        return this.instance;
    }

    defaults: UserSessionAttrs = {
        archivedReviewRequestsURL: null,
        authenticated: false,
        diffsShowExtraWhitespace: false,
        fullName: null,
        loginURL: null,
        mutedReviewRequestsURL: null,
        readOnly: false,
        sessionURL: null,
        showReviewDialogTips: true,
        timezoneOffset: '0',
        userFileAttachmentsURL: null,
        userPageURL: null,
        username: null,
        watchedReviewGroupsURL: null,
        watchedReviewRequestsURL: null,
    };

    /**********************
     * Instance variables *
     **********************/

    /** The API endpoint for archiving. */
    archivedReviewRequests: StoredItems;

    /** The API endpoint for muting. */
    mutedReviewRequests: StoredItems;

    /** The API endpoint for starring groups. */
    watchedGroups: StoredItems;

    /** The API endpoint for starring review requests. */
    watchedReviewRequests: StoredItems;

    /**
     * Initialize the model.
     */
    initialize() {
        this.watchedGroups = new StoredItems({
            url: this.get('watchedReviewGroupsURL'),
            addError: _`Must log in to add a watched item.`,
            removeError: _`Must log in to remove a watched item.`,
        });

        this.watchedReviewRequests = new StoredItems({
            url: this.get('watchedReviewRequestsURL'),
            addError: _`Must log in to add a watched item.`,
            removeError: _`Must log in to remove a watched item.`,
        });

        this.archivedReviewRequests = new StoredItems({
            url: this.get('archivedReviewRequestsURL'),
            removeError: _`Must log in to remove a archived item.`,
            addError: _`Must log in to add an archived item.`,
        });

        this.mutedReviewRequests = new StoredItems({
            url: this.get('mutedReviewRequestsURL'),
            removeError: _`Must log in to remove a muted item.`,
            addError: _`Must log in to add a muted item.`,
        });

        this._bindCookie({
            attr: 'diffsShowExtraWhitespace',
            cookieName: 'show_ew',
            deserialize: value => (value !== 'false'),
        });

        this._bindCookie({
            attr: 'showReviewDialogTips',
            cookieName: 'show_review_dialog_tips',
            deserialize: value => (value !== 'false'),
        });
    }

    /**
     * Toggle a boolean attribute.
     *
     * The attribute will be the inverse of the prior value.
     *
     * Args:
     *     attr (string):
     *         The name of the attribute to toggle.
     */
    toggleAttr(attr: string) {
        this.set(attr, !this.get(attr));
    }

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
    getAvatarHTML(
        size: number,
    ): string {
        const urls = this.get('avatarHTML') || {};

        return urls[size] || '';
    }

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
    _bindCookie(options: {
        attr: string;
        cookieName: string;
        deserialize?: (string) => unknown;
        serialize?: (unknown) => string;
    }) {
        const deserialize = options.deserialize || _.identity;
        const serialize = (options.serialize ||
                           (value => value.toString()));

        this.set(options.attr, deserialize($.cookie(options.cookieName)));

        this.on(`change:${options.attr}`, (model, value) => {
            $.cookie(options.cookieName, serialize(value), {
                path: SITE_ROOT,
            });
        });
    }
}
