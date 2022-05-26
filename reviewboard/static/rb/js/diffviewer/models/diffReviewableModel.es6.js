/**
 * Provides state and utility functions for loading and reviewing diffs.
 *
 * Model Attributes:
 *     baseFileDiffID (number):
 *         The ID of the base FileDiff.
 *
 *     fileDiffID (number):
 *         The ID of the FileDiff.
 *
 *     file (RB.DiffFile):
 *         Information on the file associated with this diff.
 *
 *     interdiffRevision (number):
 *         The revision on the end of an interdiff range.
 *
 *     interFileDiffID (number):
 *         The ID of the FileDiff on the end of an interdiff range.
 *
 *     revision (number):
 *         The revision of the FileDiff.
 *
 * See Also:
 *     :js:class:`RB.AbstractReviewable`:
 *         For the attributes defined by the base model.
 */
RB.DiffReviewable = RB.AbstractReviewable.extend({
    defaults: _.defaults({
        baseFileDiffID: null,
        file: null,
        fileDiffID: null,
        interdiffRevision: null,
        interFileDiffID: null,
        revision: null,
    }, RB.AbstractReviewable.prototype.defaults),

    commentBlockModel: RB.DiffCommentBlock,

    defaultCommentBlockFields: [
        'baseFileDiffID',
        'fileDiffID',
        'interFileDiffID',
    ],

    /**
     * Load a serialized comment and add comment blocks for it.
     *
     * Args:
     *     serializedCommentBlock (object):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(serializedCommentBlock) {
        this.createCommentBlock({
            reviewRequest: this.get('reviewRequest'),
            review: this.get('review'),
            fileDiffID: this.get('fileDiffID'),
            interFileDiffID: this.get('interFileDiffID'),
            beginLineNum: serializedCommentBlock.linenum,
            endLineNum: serializedCommentBlock.linenum +
                        serializedCommentBlock.num_lines - 1,
            serializedComments: serializedCommentBlock.comments || [],
        });
    },

    /**
     * Return the rendered diff for a file.
     *
     * The rendered file will be fetched from the server and eventually
     * returned through the promise.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         The option arguments that control the behavior of this function.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     *     oldOptions (object, optional):
     *         Previous location of the options parameter.
     *
     * Option Args:
     *     showDeleted (boolean):
     *         Determines whether or not we want to requeue the corresponding
     *         diff in order to show its deleted content.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    getRenderedDiff(options={}, context=undefined, oldOptions={}) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.DiffReviewable.getRenderedDiff was called ' +
                         'using callbacks. Callers should be updated to ' +
                         'use promises instead.');
            return RB.promiseToCallbacks(
                _.defaults({}, options, oldOptions), context,
                newOptions => this.getRenderedDiff(newOptions));
        }

        return this._fetchFragment({
            url: this._buildRenderedDiffURL({
                index: this.get('file').get('index'),
                showDeleted: options.showDeleted,
            }),
            noActivityIndicator: true,
        });
    },

    /**
     * Return a rendered fragment of a diff.
     *
     * The fragment will be fetched from the server and eventually returned
     * through the promise.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object):
     *         The option arguments that control the behavior of this function.
     *
     *     context (object, optional):
     *         Context to bind when calling callbacks.
     *
     *     oldOptions (object, optional):
     *         Previous location of the options parameter.
     *
     * Option Args:
     *     chunkIndex (string):
     *         The chunk index to load.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    getRenderedDiffFragment(options, context=undefined, oldOptions={}) {
        if (_.isFunction(options.success) ||
            _.isFunction(options.error) ||
            _.isFunction(options.complete)) {
            console.warn('RB.DiffReviewable.getRenderedDiffFragment was ' +
                         'called using callbacks. Callers should be updated ' +
                         'to use promises instead.');
            return RB.promiseToCallbacks(
                _.defaults({}, options, oldOptions), context,
                newOptions => this.getRenderedDiffFragment(newOptions));
        }

        console.assert(options.chunkIndex !== undefined,
                       'chunkIndex must be provided');

        return this._fetchFragment({
            url: this._buildRenderedDiffURL({
                chunkIndex: options.chunkIndex,
                index: this.get('file').get('index'),
                linesOfContext: options.linesOfContext,
            }),
        });
    },

    /**
     * Fetch the diff fragment from the server.
     *
     * This is used internally by getRenderedDiff and getRenderedDiffFragment
     * to do all the actual fetching.
     *
     * Args:
     *     options (object):
     *         The option arguments that control the behavior of this function.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    _fetchFragment(options) {
        return new Promise(resolve => {
            RB.apiCall(_.defaults(
                {
                    type: 'GET',
                    dataType: 'html',
                    complete: xhr => resolve(xhr.responseText),
                },
                options));
        });
    },

    /**
     * Return a URL that forms the base of a diff fragment fetch.
     *
     * Args:
     *     options (object):
     *         Options for the URL.
     *
     * Option Args:
     *     chunkIndex (number, optional):
     *         The chunk index to load.
     *
     *     index (number, optional):
     *         The file index to load.
     *
     *     linesOfContext (number, optional):
     *         The number of lines of context to load.
     *
     *     showDeleted (boolean, optional):
     *         Whether to show deleted content.
     *
     * Returns:
     *     string:
     *     The URL for fetching diff fragments.
     */
    _buildRenderedDiffURL(options={}) {
        const reviewURL = this.get('reviewRequest').get('reviewURL');
        const interdiffRevision = this.get('interdiffRevision');
        const fileDiffID = this.get('fileDiffID');
        const interFileDiffID = this.get('interFileDiffID');
        const baseFileDiffID = this.get('baseFileDiffID');
        const revision = this.get('revision');

        const revisionPart = (interdiffRevision
                              ? `${revision}-${interdiffRevision}`
                              : revision);

        const fileDiffPart = (interFileDiffID
                              ? `${fileDiffID}-${interFileDiffID}`
                              : fileDiffID);

        let url = `${reviewURL}diff/${revisionPart}/fragment/${fileDiffPart}/`;

        if (options.chunkIndex !== undefined) {
            url += `chunk/${options.chunkIndex}/`;
        }

        /* Build the query string. */
        const queryParts = [];

        if (baseFileDiffID) {
            queryParts.push(`base-filediff-id=${baseFileDiffID}`);
        }

        if (options.index !== undefined) {
            queryParts.push(`index=${options.index}`);
        }

        if (options.linesOfContext !== undefined) {
            queryParts.push(`lines-of-context=${options.linesOfContext}`);
        }

        if (options.showDeleted) {
            queryParts.push(`show-deleted=1`);
        }

        queryParts.push(`_=${TEMPLATE_SERIAL}`);

        const queryStr = queryParts.join('&');

        return `${url}?${queryStr}`;
    },
});
