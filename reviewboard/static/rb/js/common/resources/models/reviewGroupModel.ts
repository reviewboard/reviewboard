/**
 * A review group.
 */

import {
    type Result,
    spina,
} from '@beanbag/spina';

import {
    API,
    BackboneError,
} from '../../utils/apiUtils';
import {
    type BaseResourceAttrs,
    type BaseResourceResourceData,
    BaseResource,
} from './baseResourceModel';
import { UserSession } from '../../models/userSessionModel';


/**
 * Attributes for the GroupMember model.
 *
 * Version Added:
 *     7.0.1
 */
interface GroupMemberAttrs extends BaseResourceAttrs {
    /** Whether the user has been added to the group. */
    added: boolean;

    /** The username of the group member. */
    username: string;
}


/**
 * Resource data for the GroupMember model.
 *
 * Version Added:
 *     7.0.1
 */
interface GroupMemberResourceData extends BaseResourceResourceData {
    username: string;
}


/**
 * A member of a review group.
 *
 * This is used to handle adding a user to a group or removing from a group.
 */
@spina
class GroupMember extends BaseResource<
    GroupMemberAttrs,
    GroupMemberResourceData
> {
    static defaults: Result<Partial<GroupMemberAttrs>> = {
        added: false,
        loaded: true,
        username: null,
    };

    static serializedAttrs = ['username'];

    /**
     * Return a URL for this resource.
     *
     * If this represents an added user, the URL will point to
     * <groupname>/<username>/. Otherwise, it just points to <groupname>/.
     *
     * Returns:
     *     string:
     *     The URL to use when syncing the model.
     */
    url(): string {
        let url = this.get('baseURL');

        if (this.get('added')) {
            url += this.get('username') + '/';
        }

        return url;
    }

    /**
     * Return whether the group membership is "new".
     *
     * A non-added user is new, meaning the save operation will trigger
     * a POST to add the user.
     *
     * Returns:
     *     boolean:
     *     Whether this member is newly-added to the group.
     */
    isNew(): boolean {
        return !this.get('added');
    }

    /**
     * Parse the result payload.
     *
     * We don't really care about the result, so we don't bother doing any
     * work to parse.
     */
    parse(
        rsp: Partial<GroupMemberResourceData & { stat: string }>,
    ): Partial<GroupMemberAttrs> {
        // Do nothing.
        return {};
    }
}


/**
 * Attributes for the ReviewGroup model.
 *
 * Version Added:
 *     7.0.1
 */
export interface ReviewGroupAttrs extends BaseResourceAttrs {
    /** The name of the review group. */
    name: string;
}


/**
 * Resource data for the ReviewGroup model.
 *
 * Version Added:
 *     7.0.1
 */
export interface ReviewGroupResourceData extends BaseResourceResourceData {
    name: string;
    url: string;
}


/**
 * A review group.
 *
 * This provides some utility functions for working with an existing
 * review group.
 *
 * At the moment, this consists of marking a review group as
 * starred/unstarred.
 */
@spina
export class ReviewGroup extends BaseResource<
    ReviewGroupAttrs,
    ReviewGroupResourceData
> {
    static defaults: Result<Partial<ReviewGroupAttrs>> = {
        name: null,
    };

    static rspNamespace = 'group';

    /**
     * Return the URL to the review group.
     *
     * If this is a new group, the URL will point to the base groups/ URL.
     * Otherwise, it points to the URL for the group itself.
     *
     * Returns:
     *     string:
     *     The URL to use when syncing the model.
     */
    url(): string {
        let url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                  'api/groups/';

        if (!this.isNew()) {
            url += this.get('name') + '/';
        }

        return url;
    }

    /**
     * Mark a review group as starred or unstarred.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated the options and context parameters and changed to return
     *     a promise.
     *
     * Args:
     *     starred (boolean):
     *         Whether or not the group is starred.
     *
     *     options (object, optional):
     *         Additional options for the save operation, including callbacks.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    setStarred(
        starred: boolean,
        options: Backbone.ModelSaveOptions = {},
        context: unknown = undefined,
    ): Promise<void | JQueryXHR> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewGroup.setStarred was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');

            return API.promiseToCallbacks(
                options, context, newOptions => this.setStarred(starred));
        }

        const watched = UserSession.instance.watchedGroups;

        return starred ? watched.addImmediately(this)
                       : watched.removeImmediately(this);
    }

    /**
     * Add a user to this group.
     *
     * Sends the request to the server to add the user, and notifies on
     * success or failure.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     username (string):
     *         The username of the new user.
     *
     *     options (object, optional):
     *         Additional options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    addUser(
        username: string,
        options: Backbone.ModelSaveOptions = {},
        context: unknown = undefined,
    ): Promise<JQueryXHR> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewGroup.addUser was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');

            return API.promiseToCallbacks(
                options, context, newOptions => this.addUser(username));
        }

        const url = this.url() + 'users/';

        if (url && !this.isNew()) {
            const member = new GroupMember({
                baseURL: url,
                username: username,
            });

            return member.save();
        } else {
            return Promise.reject(new BackboneError(this, {
                errorText: 'Unable to add to the group.',
            }, options));
        }
    }

    /*
     * Remove a user from this group.
     *
     * Sends the request to the server to remove the user, and notifies on
     * success or failure.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     username (string):
     *         The username of the new user.
     *
     *     options (object, optional):
     *         Additional options for the save operation.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    removeUser(
        username: string,
        options: Backbone.ModelSaveOptions = {},
        context: unknown = undefined,
    ): Promise<void> {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.ReviewGroup.removeUser was called using ' +
                         'callbacks. Callers should be updated to use ' +
                         'promises instead.');

            return API.promiseToCallbacks(
                options, context, newOptions => this.removeUser(username));
        }

        const url = this.url() + 'users/';

        if (url && !this.isNew()) {
            const member = new GroupMember({
                added: true,
                baseURL: url,
                username: username,
            });

            return member.destroy();
        } else {
            return Promise.reject(new BackboneError(this, {
                errorText: 'Unable to remove from the group.',
            }, options));
        }
    }
}
