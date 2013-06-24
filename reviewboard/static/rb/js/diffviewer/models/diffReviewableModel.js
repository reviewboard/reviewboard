/*
 * Provides state and utility functions for loading and reviewing diffs.
 */
RB.DiffReviewable = RB.AbstractReviewable.extend({
    defaults: _.defaults({
        reviewRequestURL: null,
        fileIndex: null,
        fileDiffID: null,
        interFileDiffID: null,
        revision: null,
        interdiffRevision: null
    }, RB.AbstractReviewable.prototype.defaults),

    commentBlockModel: RB.AbstractCommentBlock,
    defaultCommentBlockFields: ['fileDiffID', 'interFileDiffID'],

    /*
     * Returns the rendered diff for a file.
     *
     * The rendered file will be fetched from the server and eventually
     * returned as the argument to the success callback.
     */
    getRenderedDiff: function(callbacks, context) {
        this._fetchFragment({
            url: this._buildRenderedDiffURL() +
                 '?index=' + this.get('fileIndex') + '&' + AJAX_SERIAL,
            noActivityIndicator: true
        }, callbacks, context);
    },

    /*
     * Returns a rendered fragment of a diff.
     *
     * The fragment will be fetched from the server and eventually returned
     * as the argument to the success callback.
     */
    getRenderedDiffFragment: function(options, callbacks, context) {
        console.assert(options.chunkIndex, 'chunkIndex must be provided');

        this._fetchFragment({
            url: this._buildRenderedDiffURL() + 'chunk/' +
                 options.chunkIndex + '/',
            data: {
                'index': this.get('fileIndex'),
                'lines-of-context': options.linesOfContext
            }
        }, callbacks, context);
    },

    /*
     * Fetches the diff fragment from the server.
     *
     * This is used internally by getRenderedDiff and getRenderedDiffFragment
     * to do all the actual fetching and calling of callbacks.
     */
    _fetchFragment: function(options, callbacks, context) {
        RB.apiCall(_.defaults(
            {
                type: 'GET',
                dataType: 'html'
            },
            options,
            _.bindCallbacks(callbacks, context)
        ));
    },

    /*
     * Builds a URL that forms the base of a diff fragment fetch.
     */
    _buildRenderedDiffURL: function() {
        var revisionStr,
            interdiffRevision = this.get('interdiffRevision');

        revisionStr = this.get('revision');

        if (interdiffRevision) {
            revisionStr += '-' + interdiffRevision;
        }

        return this.get('reviewRequestURL') + 'diff/' + revisionStr +
               '/fragment/' + this.get('fileDiffID') + '/';
    }
});
