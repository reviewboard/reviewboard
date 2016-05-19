/**
 * A commit in a repository.
 *
 * Model Attributes:
 *     accessible (boolean):
 *         Whether this commit appears accessible. On some version control
 *         systems, not all commits may be accessible due to ACLs or other
 *         policy mechanisms. In these cases, we shouldn't let people try to
 *         make a review request for them, because it will fail.
 *
 *     authorName (string):
 *         The name of the author of the commit.
 *
 *     date (Date):
 *         The date of the commit.
 *
 *     parent (string):
 *         The ID of the commit's parent.
 *
 *     message (string):
 *         The commit message or comment.
 *
 *     summary (string):
 *         The first line of the commit message.
 *
 *     reviewRequestURL (string):
 *         The URL of an existing review request for this commit, if one
 *         exists.
 */
RB.RepositoryCommit = RB.BaseResource.extend({
    defaults() {
        return _.defaults({
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
        date: date => date ? new Date(date) : '',
        summary: message => message.split('\n', 1)[0]
    },

    serializers: {
        date: date => date.toString()
    },

    /**
     * Parse the response from the server.
     *
     * Args:
     *     rsp (object):
     *          The response from the server.
     *
     * Returns:
     *     object:
     *     Attribute values to set on the model.
     */
    parseResourceData(rsp) {
        const data = RB.BaseResource.prototype.parseResourceData.call(
            this, rsp);

        data.accessible = rsp.date || rsp.message || rsp.author_name;

        return data;
    }
});
