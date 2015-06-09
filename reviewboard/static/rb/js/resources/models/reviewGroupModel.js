(function() {


/*
 * A member of a review group.
 *
 * This is used to handle adding a user to a group or removing from a group.
 */
var GroupMember = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            username: null,
            added: false,
            loaded: true
        }, RB.BaseResource.prototype.defaults());
    },

    serializedAttrs: ['username'],

    /*
     * Returns a URL for this resource.
     *
     * If this represents an added user, the URL will point to
     * <groupname>/<username>/. Otherwise, it just points to <groupname>/.
     */
    url: function() {
        var url = this.get('baseURL');

        if (this.get('added')) {
            url += this.get('username') + '/';
        }

        return url;
    },

    /*
     * Returns whether the group membership is "new".
     *
     * A non-added user is new, meaning the save operation will trigger
     * a POST to add the user.
     */
    isNew: function() {
        return !this.get('added');
    },

    /*
     * Parses the result payload.
     *
     * We don't really care about the result, so we don't bother doing any
     * work to parse.
     */
    parse: function() {}
});


/*
 * A registered review group.
 *
 * This provides some utility functions for working with an existing
 * review group.
 *
 * At the moment, this consists of marking a review group as
 * starred/unstarred.
 */
RB.ReviewGroup = RB.BaseResource.extend({
    defaults: _.defaults({
        name: null
    }, RB.BaseResource.prototype.defaults),

    rspNamespace: 'group',

    /*
     * Returns the URL to the review group.
     *
     * If this is a new group, the URL will point to the base groups/ URL.
     * Otherwise, it points to the URL for the group itself.
     */
    url: function() {
        var url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                  'api/groups/';

        if (!this.isNew()) {
            url += this.get('name') + '/';
        }

        return url;
    },

    /*
     * Marks a review group as starred or unstarred.
     */
    setStarred: function(starred, options, context) {
        var watched = RB.UserSession.instance.watchedGroups;

        if (starred) {
            watched.addImmediately(this, options, context);
        } else {
            watched.removeImmediately(this, options, context);
        }
    },

    /*
     * Adds a user to this group.
     *
     * Sends the request to the server to add the user, and notifies on
     * succes or failure.
     */
    addUser: function(username, options, context) {
        var url = this.url() + 'users/',
            member;

        if (url && !this.isNew()) {
            member = new GroupMember({
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
     * Removes a user from this group.
     *
     * Sends the request to the server to remove the user, and notifies on
     * succes or failure.
     */
    removeUser: function(username, options, context) {
        var url = this.url() + 'users/',
            member;

        if (url && !this.isNew()) {
            member = new GroupMember({
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
