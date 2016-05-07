/**
 * A client-side representation of a repository on the server.
 *
 * Model Attributes:
 *     filesOnly (boolean):
 *         Whether this repository is the fake "file attachments only" entry.
 *
 *     localSitePrefix (string):
 *         The URL prefix for the local site, if any.
 *
 *     name (string):
 *         The name of the repository.
 *
 *     requiresBasedir (boolean):
 *         Whether posting diffs against this repository requires the
 *         specification of a "base directory" (the relative path between the
 *         repository root and the filenames in the diff file).
 *
 *     requiresChangeNumber (boolean):
 *         Whether posting diffs against this repository requires the
 *         specification of the associated change number.
 *
 *     scmtoolName (string):
 *         The name of the SCM that this repository uses.
 *
 *     supportsPostCommit (boolean):
 *         Whether this repository supports the APIs necessary to enable the
 *         post-commit UI.
 */
RB.Repository = RB.BaseResource.extend({
    defaults() {
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

    /**
     * Initialize the model.
     */
    initialize() {
        RB.BaseResource.prototype.initialize.apply(this, arguments);

        this.branches = new RB.RepositoryBranches();
        this.branches.url = _.result(this, 'url') + 'branches/';
    },

    /**
     * Get a collection of commits from a given starting point.
     *
     * Args:
     *     options (object):
     *         Options for the commits collection.
     *
     * Option Args:
     *     start (string):
     *         The starting commit (which will be the most recent commit
     *         listed).
     *
     *     branch (string):
     *         The branch to fetch commits from.
     *
     * Returns:
     *     RB.RepositoryCommits:
     *     The commits collection.
     */
    getCommits(options) {
        return new RB.RepositoryCommits([], {
            urlBase: _.result(this, 'url') + 'commits/',
            start: options.start,
            branch: options.branch
        });
    },

    /**
     * Return the URL for syncing the model.
     *
     * Returns:
     *     string:
     *     The URL to use when syncing the model.
     */
    url() {
        const url = SITE_ROOT + (this.get('localSitePrefix') || '') +
                    'api/repositories/';

        return this.isNew() ? url : `${url}${this.id}/`;
    }
});
