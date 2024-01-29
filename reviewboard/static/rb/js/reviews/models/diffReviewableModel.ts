/**
 * Provides state and utility functions for loading and reviewing diffs.
 */

import { spina } from '@beanbag/spina';

import {
    AbstractReviewable,
    AbstractReviewableAttrs,
} from './abstractReviewableModel';
import {
    DiffCommentBlock,
    SerializedDiffComment,
} from './diffCommentBlockModel';


/**
 * Attributes for the DiffReviewable model.
 *
 * Version Added:
 *     7.0
 */
export interface DiffReviewableAttrs extends AbstractReviewableAttrs {
    /** The ID of the base FileDiff. */
    baseFileDiffID: number;

    /** Information on the file associated with this diff. */
    file: RB.DiffFile;

    /** The ID of the FileDiff. */
    fileDiffID: number;

    /** The ID of the FileDiff on the end of an interdiff range. */
    interFileDiffID: number;

    /** The revision on the end of an interdiff range. */
    interdiffRevision: number;

    /** Whether the diff has been published. */
    public: boolean;

    /** The revision of the FileDiff. */
    revision: number;
}


/**
 * Provides state and utility functions for loading and reviewing diffs.
 *
 * See Also:
 *     :js:class:`RB.AbstractReviewable`:
 *         For the attributes defined by the base model.
 */
@spina
export class DiffReviewable
    extends AbstractReviewable<DiffReviewableAttrs, DiffCommentBlock> {
    static defaults: DiffReviewableAttrs = _.defaults({
        baseFileDiffID: null,
        file: null,
        fileDiffID: null,
        interFileDiffID: null,
        interdiffRevision: null,
        public: false,
        revision: null,
    }, super.defaults);

    static commentBlockModel = DiffCommentBlock;

    static defaultCommentBlockFields = [
        'baseFileDiffID',
        'fileDiffID',
        'interFileDiffID',
        'public',
    ];

    /**
     * Load a serialized comment and add comment blocks for it.
     *
     * Args:
     *     serializedCommentBlock (object):
     *         The serialized data for the new comment block(s).
     */
    loadSerializedCommentBlock(
        serializedCommentBlock: SerializedDiffComment,
    ) {
        this.createCommentBlock({
            beginLineNum: serializedCommentBlock.linenum,
            endLineNum: (serializedCommentBlock.linenum as number) +
                        (serializedCommentBlock.num_lines as number) - 1,
            fileDiffID: this.get('fileDiffID'),
            interFileDiffID: this.get('interFileDiffID'),
            public: this.get('public'),
            review: this.get('review'),
            reviewRequest: this.get('reviewRequest'),
            serializedComments: serializedCommentBlock.comments || [],
        });
    }

    /**
     * Return the rendered diff for a file.
     *
     * The rendered file will be fetched from the server and eventually
     * returned through the promise.
     *
     * Version Changed:
     *     7.0:
     *     Removed old callbacks-style invocation.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object, optional):
     *         The option arguments that control the behavior of this function.
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
    getRenderedDiff(
        options: {
            showDeleted?: boolean;
        } = {},
    ): Promise<string> {
        return this._fetchFragment({
            noActivityIndicator: true,
            url: this._buildRenderedDiffURL({
                index: this.get('file').get('index'),
                showDeleted: options.showDeleted,
            }),
        });
    }

    /**
     * Return a rendered fragment of a diff.
     *
     * The fragment will be fetched from the server and eventually returned
     * through the promise.
     *
     * Version Changed:
     *     7.0:
     *     Removed old callbacks-style invocation.
     *
     * Version Changed:
     *     5.0:
     *     Deprecated callbacks and added a promise return value.
     *
     * Args:
     *     options (object):
     *         The option arguments that control the behavior of this function.
     *
     * Option Args:
     *     chunkIndex (number):
     *         The chunk index to load.
     *
     *     linesOfContext (number):
     *         The number of additional lines of context to include.
     *
     * Returns:
     *     Promise:
     *     A promise which resolves when the operation is complete.
     */
    getRenderedDiffFragment(
        options: {
            chunkIndex: number;
            linesOfContext?: number;
        },
    ): Promise<string> {
        console.assert(options.chunkIndex !== undefined,
                       'chunkIndex must be provided');

        return this._fetchFragment({
            url: this._buildRenderedDiffURL({
                chunkIndex: options.chunkIndex,
                index: this.get('file').get('index'),
                linesOfContext: options.linesOfContext,
            }),
        });
    }

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
    _fetchFragment(
        options, // TODO TYPING: convert once RB.apiCall has an interface
    ): Promise<string> {
        return new Promise<string>(resolve => {
            RB.apiCall(_.defaults(
                {
                    complete: xhr => resolve(xhr.responseText),
                    dataType: 'html',
                    type: 'GET',
                },
                options));
        });
    }

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
    _buildRenderedDiffURL(
        options: {
            chunkIndex?: number;
            index?: number;
            linesOfContext?: number;
            showDeleted?: boolean;
        } = {},
    ): string {
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
    }
}
