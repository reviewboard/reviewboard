/*
 * Provides state and utility functions for loading and reviewing diffs.
 */
RB.DiffReviewable = RB.AbstractReviewable.extend({
    defaults: _.defaults({
        reviewRequestURL: null,
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
    getRenderedDiff: function(options, callbacks, context) {
        console.assert(_.has(options, 'fileIndex'),
                       'fileIndex must be provided');

        this._fetchFragment({
            url: this._buildRenderedDiffURL(options) +
                 '?index=' + options.fileIndex + '&' + AJAX_SERIAL,
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
        console.assert(_.has(options, 'fileIndex'),
                       'fileIndex must be provided');
        console.assert(_.has(options, 'chunkIndex'),
                       'chunkIndex must be provided');

        this._fetchFragment({
            url: this._buildRenderedDiffURL(options) + 'chunk/' +
                 options.chunkIndex + '/',
            data: {
                'index': options.fileIndex,
                'lines-of-context': options.linesOfContext || undefined
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
    _buildRenderedDiffURL: function(options) {
        var revisionStr,
            reviewRequestURL = options.reviewRequestURL ||
                               this.get('reviewRequestURL'),
            interdiffRevision = this.get('interdiffRevision');

        revisionStr = this.get('revision');

        if (interdiffRevision) {
            revisionStr += '-' + interdiffRevision;
        }

        return reviewRequestURL + 'diff/' + revisionStr + '/fragment/' +
               this.get('fileDiffID') + '/';
    }
});
