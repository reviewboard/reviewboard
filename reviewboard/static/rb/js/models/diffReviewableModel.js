/*
 * Provides state and utility functions for loading and reviewing diffs.
 *
 * TODO: This should be made to use AbstractReviewable when we move the rest
 *       of the diff viewer onto it. That would require DiffCommentBlock and
 *       other functionality.
 */
RB.DiffReviewable = Backbone.Model.extend({
    defaults: {
        reviewRequestURL: null,
        revision: null,
        interdiffRevision: null
    },

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
                type: "GET",
                dataType: "html"
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
                               this.get('reviewRequestURL');

        console.assert(_.has(options, 'fileDiffID'),
                       'fileDiffID must be provided');

        if (options.revision === undefined) {
            options.revision = this.get('revision');
        }

        if (options.interdiffRevision === undefined) {
            options.interdiffRevision = this.get('interdiffRevision');
        }

        revisionStr = options.revision;

        if (options.interdiffRevision) {
            revisionStr += '-' + options.interdiffRevision;
        }

        return reviewRequestURL + 'diff/' + revisionStr + '/fragment/' +
               options.fileDiffID + '/';
    }
});
