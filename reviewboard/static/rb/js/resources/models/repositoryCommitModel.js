/*
 * A commit in a repository.
 */
RB.RepositoryCommit = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
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
            return new Date(date);
        },

        summary: function(message) {
            return message.split('\n', 1)[0];
        }
    },

    serializers: {
        date: function(date) {
            return date.toString();
        }
    }
});
