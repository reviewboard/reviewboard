/**
 * A collection of RB.DiffReviewable instances.
 *
 * This manages a collection of :js:class:`RB.DiffReviewable`s and can
 * populate itself based on changes to a collection of files.
 *
 * When repopulating, this will emit a ``populating`` event. After populating,
 * it will emit a ``populated`` event.
 */
RB.DiffReviewableCollection = Backbone.Collection.extend({
    model: RB.DiffReviewable,

    /**
     * Initialize the collection.
     *
     * Args:
     *     models (Array):
     *         Optional array of models.
     *
     *     options (object):
     *         Options for the collection.
     *
     * Option Args:
     *     reviewRequest (RB.ReviewRequest):
     *         The review request for the collection. This must be provided.
     */
    initialize(models, options) {
        this.reviewRequest = options.reviewRequest;
    },

    /**
     * Watch for changes to a collection of files.
     *
     * When the files change (and when invoking this method), this collection
     * will be rebuilt based on those files.
     *
     * Args:
     *     files (RB.DiffFileCollection):
     *         The collection of files to watch.
     */
    watchFiles(files) {
        this.listenTo(files, 'reset', () => this._populateFromFiles(files));
        this._populateFromFiles(files);
    },

    /**
     * Populate this collection from a collection of files.
     *
     * This will clear this collection and then loop through each file,
     * adding a corresponding :js:class:`RB.DiffReviewable`.
     *
     * After clearing, but prior to adding any entries, this will emit a
     * ``populating`` event. After all reviewables have been added, this
     * will emit a ``populated`` event.
     *
     * Args:
     *     files (RB.DiffFileCollection):
     *         The collection of files to populate from.
     */
    _populateFromFiles(files) {
        const reviewRequest = this.reviewRequest;

        console.assert(reviewRequest,
                       'RB.DiffReviewableCollection.reviewRequest must be set');

        this.reset();
        this.trigger('populating');

        files.each(file => {
            const filediff = file.get('filediff');
            const interfilediff = file.get('interfilediff');
            let interdiffRevision = null;

            if (interfilediff) {
                interdiffRevision = interfilediff.revision;
            } else if (file.get('forceInterdiff')) {
                interdiffRevision = file.get('forceInterdiffRevision');
            }

            this.add({
                baseFileDiffID: file.get('baseFileDiffID'),
                reviewRequest: reviewRequest,
                file: file,
                fileDiffID: filediff.id,
                interFileDiffID: interfilediff ? interfilediff.id : null,
                revision: filediff.revision,
                interdiffRevision: interdiffRevision,
                serializedCommentBlocks: file.get('commentCounts'),
            });
        });

        this.trigger('populated');
    },
});
