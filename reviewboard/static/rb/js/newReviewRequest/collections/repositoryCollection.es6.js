/**
 * A collection for displaying repositories in the "New Review Request" page.
 *
 * Version Added:
 *     4.0.7
 */
RB.RepositoryCollection = RB.BaseCollection.extend({
    model: RB.Repository,

    /**
     * Initialize the collection.
     *
     * Args:
     *     models (Array of object):
     *         Initial models for the collection.
     *
     *     options (object):
     *         Options for the collection.
     */
    initialize(models, options) {
        this.collection = new RB.ResourceCollection(options.repositories, {
            extraQueryData: {},
            model: this.model,
        });
        this.collection._fetchURL = SITE_ROOT + options.localSitePrefix +
                                    'api/repositories/';

        this._fileAttachmentRepo = new RB.Repository({
            name: gettext('(None - File attachments only)'),
            scmtoolName: '',
            localSitePrefix: options.localSitePrefix,
            supportsPostCommit: false,
            filesOnly: true,
        });

        this.listenTo(this.collection, 'add', this.add);
        this.listenTo(this.collection, 'remove', this.remove);
        this.listenTo(this.collection, 'reset', this._rebuild);

        this._rebuild();
    },

    /**
     * Rebuild the list of models.
     */
    _rebuild() {
        this.reset([this._fileAttachmentRepo].concat(this.collection.models));
    },

    /**
     * Perform a search.
     *
     * Args:
     *     query (string):
     *         The query to search for in repository names and paths.
     */
    search(query) {
        this.collection.extraQueryData.q = query;
        this.collection.fetch({
            success: () => this._rebuild(),
        });
    },
});
