/*
 * A commit in a repository.
 */
RB.RepositoryCommit = Backbone.Model.extend({
    defaults: {
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
    },

    parse: function(object) {
        return {
            accessible: object.date || object.message || object.author_name,
            authorName: object.author_name,
            date: object.date ? new Date(object.date) : null,
            id: object.id,
            parent: object.parent,
            message: object.message,
            summary: object.message.split('\n', 1)[0],
            reviewRequestURL: object.review_request_url
        };
    }
});
