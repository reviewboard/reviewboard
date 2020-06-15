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

        let url = this._buildRenderedDiffURL();

        if (url.includes('?')) {
            url += '&';
        } else {
            url += '?';
        }

        url += 'index=';
        url += this.get('file').get('index');

        if (options.showDeleted) {
            url += '&show-deleted=1';
        }

        url += '&' + TEMPLATE_SERIAL;

        return this._fetchFragment({
            url: url,
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
            url: `${this._buildRenderedDiffURL()}chunk/${options.chunkIndex}/`,
            data: {
                'index': this.get('file').get('index'),
                'lines-of-context': options.linesOfContext,
            }
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
     * Returns:
     *     string:
     *     The URL for fetching diff fragments.
     */
    _buildRenderedDiffURL() {
        const interdiffRevision = this.get('interdiffRevision');
        const interFileDiffID = this.get('interFileDiffID');
        const baseFileDiffID = this.get('baseFileDiffID');
        let revisionStr = this.get('revision');

        if (interdiffRevision) {
            revisionStr += '-' + interdiffRevision;
        }

        return this.get('reviewRequest').get('reviewURL') + 'diff/' +
               revisionStr + '/fragment/' + this.get('fileDiffID') +
               (interFileDiffID ? '-' + interFileDiffID : '') +
               '/' +
               (baseFileDiffID ? '?base-filediff-id=' + baseFileDiffID : '');
    },
});
