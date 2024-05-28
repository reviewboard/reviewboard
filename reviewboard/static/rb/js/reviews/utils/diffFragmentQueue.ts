/**
 * Queue for loading diff fragments.
 */

import { DataUtils } from 'reviewboard/common';


/**
 * Options for the DiffFragmentQueue.
 *
 * Version Added:
 *     8.0
 */
export interface DiffFragmentQueueOptions {
    /** The prefix to use for container element IDs. */
    containerPrefix: string;

    /** Options to pass to each :js:class:`RB.DiffFragmentView`. */
    diffFragmentViewOptions?: unknown; // TODO TYPING

    /**
     * The URL for the review request.
     */
    reviewRequestPath: string;
}


/**
 * Data for a queued fragment load operation.
 *
 * Version Added:
 *     8.0
 */
interface QueuedLoad {
    /** The ID of the comment to load the fragment for. */
    commentID: string;

    /** An optional callback for when the fragment is rendered. */
    onFragmentRendered: ((view: RB.DiffFragmentView) => void) | null;
}


/**
 * Queue for loading diff fragments.
 *
 * This is used to load diff fragments one-by-one, and to intelligently
 * batch the loads to only fetch at most one set of fragments per file.
 *
 * Version Changed:
 *     8.0:
 *     Changed to be a regular class instead of a view subclass, and renamed
 *     from DiffFragmentQueueView.
 */
export class DiffFragmentQueue {
    /**********************
     * Instance variables *
     **********************/

    /** The prefix to use for container element IDs. */
    #containerPrefix: string;

    /** Options to pass to each :js:class:`RB.DiffFragmentView`. */
    #diffFragmentViewOptions: unknown; // TODO TYPING

    /** The base URL for loading diff fragments. */
    #fragmentsBasePath: string;

    /**
     * The queued fragments.
     *
     * This is public for consumption in unit tests.
     */
    _queuedFragments: Record<string, QueuedLoad[]> = {};

    /**
     * Saved fragment contents.
     *
     * This is public for consumption in unit tests.
     */
    _savedFragments: Record<string, string> = {};

    /**
     * Initialize the queue.
     *
     * Args:
     *     options (DiffFragmentQueueOptions):
     *         Options passed to this view.
     */
    constructor(options: DiffFragmentQueueOptions) {
        this.#containerPrefix = options.containerPrefix;
        this.#diffFragmentViewOptions = options.diffFragmentViewOptions || {};
        this.#fragmentsBasePath =
            `${options.reviewRequestPath}_fragments/diff-comments/`;
    }

    /**
     * Queue the load of a diff fragment from the server.
     *
     * This will be added to a list, which will fetch the comments in batches
     * based on file IDs.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment to queue.
     *
     *     key (string):
     *         The key for the queue. Each comment with the same key will be
     *         loaded in a batch. This will generally be the ID of a file.
     *
     *     onFragmentRendered (function, optional):
     *         Optional callback for when the view for the fragment has
     *         rendered. Contains the view as a parameter.
     */
    queueLoad(
        commentID: string,
        key: string,
        onFragmentRendered?: (view: RB.DiffFragmentView) => void,
    ) {
        const queue = this._queuedFragments;

        if (!queue[key]) {
            queue[key] = [];
        }

        queue[key].push({
            commentID: commentID,
            onFragmentRendered: onFragmentRendered || null,
        });
    }

    /**
     * Save a comment's loaded diff fragment for the next load operation.
     *
     * If the comment's diff fragment was already loaded, it will be
     * temporarily stored until the next load operation involving that
     * comment. Instead of loading the fragment from the server, the saved
     * fragment's HTML will be used instead.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment to save.
     */
    saveFragment(commentID: string) {
        const $el = this.#getCommentContainer(commentID);

        if ($el.length === 1 && $el.data('diff-fragment-view')) {
            this._savedFragments[commentID] = $el.html();
        }
    }

    /**
     * Load all queued diff fragments.
     *
     * The diff fragments for each keyed set in the queue will be loaded as
     * a batch. The resulting fragments will be injected into the DOM.
     *
     * Any existing fragments that were saved will be loaded from the cache
     * without requesting them from the server.
     */
    async loadFragments() {
        if (_.isEmpty(this._queuedFragments) &&
            _.isEmpty(this._savedFragments)) {
            return;
        }

        for (const queuedLoads of Object.values(this._queuedFragments)) {
            const pendingCommentIDs: string[] = [];
            const onFragmentRenderedFuncs: {
                [key: string]: (view: RB.DiffFragmentView) => void;
            } = {};

            /*
             * Check if there are any comment IDs that have been saved.
             * We don't need to reload these from the server.
             */
            for (let i = 0; i < queuedLoads.length; i++) {
                const queuedLoad = queuedLoads[i];
                const commentID = queuedLoad.commentID;
                const onFragmentRendered =
                    (typeof queuedLoad.onFragmentRendered === 'function')
                    ? queuedLoad.onFragmentRendered
                    : null;

                if (this._savedFragments.hasOwnProperty(commentID)) {
                    const html = this._savedFragments[commentID];

                    const $container = this.#getCommentContainer(commentID);
                    console.assert($container);

                    let view = $container.data('diff-fragment-view');

                    if (view) {
                        view.$el.html(html);
                        view.render();
                    } else {
                        view = this.#renderFragment($container, commentID,
                                                    html);
                    }

                    if (onFragmentRendered) {
                        onFragmentRendered(view);
                    }

                    delete this._savedFragments[commentID];
                } else {
                    pendingCommentIDs.push(commentID);
                    onFragmentRenderedFuncs[commentID] =
                        onFragmentRendered;
                }
            }

            if (pendingCommentIDs.length > 0) {
                /*
                 * There are some comment IDs we don't have. Load these
                 * from the server.
                 *
                 * Once these are loaded, they'll call next() on the queue
                 * to process the next batch.
                 */
                await this.#loadDiff(pendingCommentIDs.join(','), {
                    onFragmentRendered: (commentID, view) => {
                        if (onFragmentRenderedFuncs[commentID]) {
                            onFragmentRenderedFuncs[commentID](view);
                        }
                    },
                });
            }
        }

        // Clear the list.
        this._queuedFragments = {};
    }

    /**
     * Return the container for a particular comment.
     *
     * Args:
     *     commentID (string):
     *         The ID of the comment.
     *
     * Returns:
     *     jQuery:
     *     The comment container, wrapped in a jQuery element. The caller
     *     may want to check the length to be sure the container was found.
     */
    #getCommentContainer(
        commentID: string,
    ): JQuery {
        return $(`#${this.#containerPrefix}_${commentID}`);
    }

    /**
     * Load a diff fragment for the given comment IDs and options.
     *
     * This will construct the URL for the relevant diff fragment and load
     * it from the server.
     *
     * Args:
     *     commentIDs (string):
     *         A string of comment IDs to load fragments for.
     *
     *     options (object, optional):
     *         Options for the loaded diff fragments.
     *
     * Option Args:
     *     linesOfContext (string):
     *         The lines of context to load for the diff. This is a string
     *         containing a comma-separated set of line counts in the form
     *         of ``numLinesBefore,numLinesAfter``.
     *
     *     onDone (function):
     *         A function to call after the diff has been loaded.
     *
     *     queueName (string):
     *         The name of the load queue. This is used to load batches of
     *         fragments sequentially.
     */
    async #loadDiff(
        commentIDs: string,
        options: {
            linesOfContext?: string;
            onDone?: () => void;
            onFragmentRendered?: (commentID: string,
                                  view: RB.DiffFragmentView) => void;
        } = {},
    ) {
        const containerPrefix = this.#containerPrefix;
        const queryArgs = new URLSearchParams();
        const onFragmentRendered = (
            typeof options.onFragmentRendered === 'function'
            ? options.onFragmentRendered
            : null);

        if (options.linesOfContext !== undefined) {
            queryArgs.append('lines_of_context',
                             options.linesOfContext);
        }

        if (!containerPrefix.includes('draft')) {
            queryArgs.append('allow_expansion', '1');
        }

        queryArgs.append('_', TEMPLATE_SERIAL);

        const rsp = await fetch(
            `${this.#fragmentsBasePath}${commentIDs}/?${queryArgs}`);
        const arrayBuffer = await rsp.arrayBuffer();

        const dataView = new DataView(arrayBuffer);
        const len = dataView.byteLength;
        let pos = 0;
        let done = false;

        while (!done) {
            const parsed = this.#parseDiffFragmentFromPayload(
                arrayBuffer, dataView, pos);

            pos = parsed.pos;
            done = (pos >= len);

            const [commentID, html] = await parsed.load();

            /* Set the HTML in the container. */
            const containerID = `#${containerPrefix}_${commentID}`;
            const $container = $(containerID);

            if ($container.length === 0) {
                /*
                 * This doesn't actually exist. We may be dealing with
                 * inconsistent state due to something missing in the
                 * database. We don't want to break the page if this
                 * happens, so log and skip the entry.
                 */
                console.error('Unable to find container %s for ' +
                              'comment ID %s. There may be missing ' +
                              'state in the database.',
                              containerID, commentID);
            } else {
                const view = this.#renderFragment(
                    $(`#${containerPrefix}_${commentID}`),
                    commentID,
                    html);

                if (onFragmentRendered) {
                    onFragmentRendered(commentID, view);
                }
            }
        }

        if (typeof options.onDone === 'function') {
            /*
             * We've parsed and rendered all fragments, so we're
             * officially done.
             */
            options.onDone();
        }
    }

    /**
     * Parse a single diff fragment from the payload.
     *
     * This will parse out information about the fragment (the comment ID and
     * HTML) and return a response containing the new position and a function
     * to call in order to load the parsed fragment.
     *
     * Args:
     *     arrayBuffer (ArrayBuffer):
     *         The array buffer being parsed.
     *
     *     dataView (DataView):
     *         The data view on top of the array buffer, used to extract
     *         information.
     *
     *     pos (number):
     *         The current position within the array buffer.
     *
     * Returns:
     *     object:
     *     An object with two keys:
     *
     *     ``pos``:
     *         The next position to parse.
     *
     *     ``load``:
     *         A function for loading the fragment content. This takes a
     *         callback function as an argument containing ``commentID`` and
     *         ``html`` arguments.
     */
    #parseDiffFragmentFromPayload(
        arrayBuffer: ArrayBuffer,
        dataView: DataView,
        pos: number,
    ): {
        load: () => Promise<[string, string]>;
        pos: number;
    } {
        /* Read the comment ID. */
        const commentID = dataView.getUint32(pos, true);
        pos += 4;

        /* Read the length of the HTML. */
        const htmlLen = dataView.getUint32(pos, true);
        pos += 4;

        /* Read the HTML position for later. */
        const htmlStart = pos;
        pos += htmlLen;

        return {
            async load(): Promise<[string, string]> {
                const html = await DataUtils.readBlobAsString(
                    new Blob([arrayBuffer.slice(htmlStart,
                                                htmlStart + htmlLen)]));

                return [commentID.toString(), html];
            },
            pos: pos,
        };
    }

    /**
     * Render a diff fragment on the page.
     *
     * This will set up a view for the diff fragment, if one is not already
     * created, and render it on the page.
     *
     * It will also mark the fragment for updates with the scroll manager
     * so that if the user is scrolled to a location past the fragment, the
     * resulting size change for the fragment won't cause the page to jump.
     *
     * Args:
     *     $container (jQuery):
     *         The container element where the fragment will be injected.
     *
     *     commentID (string):
     *         The ID of the comment.
     *
     *     html (string):
     *         The HTML contents of the fragment.
     */
    #renderFragment(
        $container: JQuery,
        commentID: string,
        html: string,
    ) {
        RB.scrollManager.markForUpdate($container);

        $container.html(html);

        let view = $container.data('diff-fragment-view');

        if (!view) {
            view = new RB.DiffFragmentView(_.defaults({
                el: $container,
                loadDiff: async options => {
                    RB.setActivityIndicator(true, {type: 'GET'});

                    /*
                     * TODO: Once DiffFragmentView is converted to expect the
                     * loadDiff function to be async, remove the onDone stuff
                     * here.
                     */
                    await this.#loadDiff(
                        commentID,
                        _.omit(options, 'onDone'));

                    RB.setActivityIndicator(false, {});

                    if (options.onDone) {
                        options.onDone();
                    }
                },
            }, this.#diffFragmentViewOptions));

            $container.data('diff-fragment-view', view);
        }

        view.render();

        RB.scrollManager.markUpdated($container);

        return view;
    }
}
