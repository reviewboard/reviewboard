/*
 * A client-side representation of a repository on the server.
 */
RB.Repository = RB.BaseResource.extend({
    defaults: function() {
        return _.defaults({
            filesOnly: false,
            localSitePrefix: null,
            name: null,
            requiresBasedir: false,
            requiresChangeNumber: false,
            scmtoolName: null,
            supportsPostCommit: false
        }, RB.BaseResource.prototype.defaults());
    },

    rspNamespace: 'repository',

    /*
     * Initialize the model.
     */
    initialize: function() {
        RB.BaseResource.prototype.initialize.apply(this, arguments);

        this.branches = new RB.RepositoryBranches();
        this.branches.url = _.result(this, 'url') + 'branches/';
    },

    /*
     * Get a collection of commits from a given starting point.
     *
     * 'options' may have the following set:
     *
     *     * 'start'  - The starting commit (this will be the most recent
     *                  commit shown).
     *     * 'branch' - The branch to fetch commits from.
     */
    getCommits: function(options) {
        return new RB.RepositoryCommits([], {
            urlBase: _.result(this, 'url') + 'commits/',
            start: options.start,
            branch: options.branch
        });
    },

    /*
     * Override for BaseResource.url.
     */
    url: function() {
        var url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                  'api/repositories/';

        if (!this.isNew()) {
            url += this.id + '/';
        }

        return url;
    }
});
