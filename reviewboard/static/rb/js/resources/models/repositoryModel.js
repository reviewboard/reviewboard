/*
 * A client-side representation of a repository on the server.
 */
RB.Repository = RB.BaseResource.extend({
    defaults: {
        name: null,
        localSitePrefix: null
    },

    initialize: function() {
        RB.BaseResource.prototype.initialize.apply(this, arguments);

        this.branches = new RB.RepositoryBranches();
        this.branches.url = _.result(this, 'url') + 'branches/';
    },

    getCommits: function(startCommit) {
        return new RB.RepositoryCommits([], {
            urlBase: _.result(this, 'url') + 'commits/',
            start: startCommit
        });
    },

    url: function() {
        var url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                  'api/repositories/';

        if (!this.isNew()) {
            url += this.id + '/';
        }

        return url;
    }
});
