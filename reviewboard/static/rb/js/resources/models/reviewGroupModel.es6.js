(function() {


/**
 * A member of a review group.
 *
 * This is used to handle adding a user to a group or removing from a group.
 */
const GroupMember = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            username: null,
            added: false,
            loaded: true
        }, RB.BaseResource.prototype.defaults());
    },

    serializedAttrs: ['username'],

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
    url() {
        let url = this.get('baseURL');

        if (this.get('added')) {
            url += this.get('username') + '/';
        }

        return url;
    },

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
    isNew() {
        return !this.get('added');
    },

    /**
     * Parse the result payload.
     *
     * We don't really care about the result, so we don't bother doing any
     * work to parse.
     */
    parse() {}
});


/**
 * A review group.
 *
 * This provides some utility functions for working with an existing
 * review group.
 *
 * At the moment, this consists of marking a review group as
 * starred/unstarred.
 */
RB.ReviewGroup = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
            name: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'group',

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
    url() {
        let url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                  'api/groups/';

        if (!this.isNew()) {
            url += this.get('name') + '/';
        }

        return url;
    },

    /**
     * Mark a review group as starred or unstarred.
     *
     * Args:
     *     starred (boolean):
     *         Whether or not the group is starred.
     *
     *     options (object):
     *         Additional options for the save operation, including callbacks.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    setStarred(starred, options, context) {
        const watched = RB.UserSession.instance.watchedGroups;

        if (starred) {
            watched.addImmediately(this, options, context);
        } else {
            watched.removeImmediately(this, options, context);
        }
    },

    /**
     * Add a user to this group.
     *
     * Sends the request to the server to add the user, and notifies on
     * succes or failure.
     *
     * Args:
     *     username (string):
     *         The username of the new user.
     *
     *     options (object):
     *         Additional options for the save operation, including callbacks.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    addUser(username, options, context) {
        const url = this.url() + 'users/';

        if (url && !this.isNew()) {
            const member = new GroupMember({
                username: username,
                baseURL: url
            });

            member.save(options, context);
        } else if (options && _.isFunction(options.error)) {
            options.error.call({
                errorText: 'Unable to add to the group.'
            });
        }
    },

    /*
     * Remove a user from this group.
     *
     * Sends the request to the server to remove the user, and notifies on
     * succes or failure.
     *
     * Args:
     *     username (string):
     *         The username of the new user.
     *
     *     options (object):
     *         Additional options for the save operation, including callbacks.
     *
     *     context (object):
     *         Context to bind when calling callbacks.
     */
    removeUser(username, options, context) {
        const url = this.url() + 'users/';

        if (url && !this.isNew()) {
            const member = new GroupMember({
                username: username,
                baseURL: url,
                added: true
            });

            member.destroy(options, context);
        } else if (options && _.isFunction(options.error)) {
            options.error.call({
                errorText: 'Unable to remove from the group.'
            });
        }
    }
});


})();
