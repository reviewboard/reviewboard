/*
 * A commit in a repository.
 */
RB.RepositoryCommit = Backbone.Model.extend({
    defaults: {
        authorName: null,
        date: null,
        parent: null,
        message: null,
        summary: null,
        reviewRequestURL: null
    },

    parse: function(object) {
        return {
            authorName: object.author_name,
            date: new Date(object.date),
            id: object.id,
            parent: object.parent,
            message: object.message,
            summary: object.message.split('\n', 1)[0],
            reviewRequestURL: object.review_request_url
        };
    }
});
