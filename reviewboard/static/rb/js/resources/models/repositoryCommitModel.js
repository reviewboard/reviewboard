/*
 * A commit in a repository.
 */
RB.RepositoryCommit = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            /*
             * Whether this commit appears accessible.
             *
             * On Subversion, a commit will be inaccessible if blocked by ACLs,
             * and will appear basically empty. No author, no commit message, no
             * date.
             */
            accessible: true,

            authorName: null,
            date: null,
            parent: null,
            message: null,
            summary: null,
            reviewRequestURL: null
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'commits',

    deserializedAttrs: [
        'authorName',
        'date',
        'id',
        'parent',
        'message',
        'summary',
        'reviewRequestURL'
    ],

    serializedAttrs: [
        'authorName',
        'date',
        'id',
        'parent',
        'message',
        'reviewRequestURL'
    ],

    attrToJsonMap: {
        authorName: 'author_name',
        reviewRequestURL: 'review_request_url',
        summary: 'message'
    },

    deserializers: {
        date: function(date) {
            return date ? new Date(date) : '';
        },

        summary: function(message) {
            return message.split('\n', 1)[0];
        }
    },

    serializers: {
        date: function(date) {
            return date.toString();
        }
    },

    parseResourceData: function(rsp) {
        var data = RB.BaseResource.prototype.parseResourceData.call(this, rsp);

        data.accessible = rsp.date || rsp.message || rsp.author_name;

        return data;
    }
});
