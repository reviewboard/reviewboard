/**
 * A page view for the diff viewer.
 */
import { Router, spina } from '@beanbag/spina';

import { UserSession } from 'reviewboard/common';

import { DiffViewerPage } from '../models/diffViewerPageModel';
import { DiffFileIndexView } from './diffFileIndexView';
import {
    ReviewablePageView,
    ReviewablePageViewOptions,
} from './reviewablePageView';


/** Options for adding a toggle button to the diff view. */
interface ToggleButtonOptions {
    /** The description of the active state and what clicking will do. */
    activeDescription: string;

    /** The label text for the active state. */
    activeText: string;

    /** The ID to use for the button element. */
    id: string;

    /** The description of the inactive state and what clicking will do. */
    inactiveDescription: string;

    /** The label text for the inactive state. */
    inactiveText: string;

    /** The default active state. */
    isActive: boolean;

    /** The callback for when the active state is explicitly toggled. */
    onToggled: (isToggled: boolean) => void;
}


/**
 * A page view for the diff viewer.
 *
 * This provides functionality for the diff viewer page for managing the
 * loading and display of diffs, and all navigation around the diffs.
 */
@spina({
    mixins: [RB.KeyBindingsMixin],
})
export class DiffViewerPageView extends ReviewablePageView<
    DiffViewerPage
> {
    static SCROLL_BACKWARD = -1;
    static SCROLL_FORWARD = 1;

    static ANCHOR_COMMENT = 1;
    static ANCHOR_FILE = 2;
    static ANCHOR_CHUNK = 4;

    /** Number of pixels to offset when scrolling to anchors. */
    static DIFF_SCROLLDOWN_AMOUNT = 15;

    static fileEntryTemplate = _.template(dedent`
        <div class="diff-container">
         <div class="diff-box">
          <table class="sidebyside loading <% if (newFile) { %>newfile<% } %>"
                 id="file_container_<%- id %>">
           <thead>
            <tr class="filename-row">
             <th>
              <span class="djblets-o-spinner"></span>
              <%- filename %>
             </th>
            </tr>
           </thead>
          </table>
         </div>
        </div>
    `);

    static viewToggleButtonContentTemplate = _.template(dedent`
        <span class="fa <%- iconClass %>"></span> <%- text %>
    `);

    /* Template for code line link anchor */
    static anchorTemplate = _.template(
        '<a name="<%- anchorName %>" class="highlight-anchor"></a>');

    keyBindings = {
        'aAKP<m': '_selectPreviousFile',
        'fFJN>': '_selectNextFile',
        'sSkp,': '_selectPreviousDiff',
        'dDjn.': '_selectNextDiff',
        '[x': '_selectPreviousComment',
        ']c': '_selectNextComment',
        '\x0d': '_recenterSelected',
        'rR': '_createComment',
    };

    /**********************
     * Instance variables *
     **********************/

    #$controls: JQuery = null;
    #$diffs: JQuery = null;
    #$highlightedChunk: JQuery = null;
    #$window: JQuery<Window>;
    #chunkHighlighter: RB.ChunkHighlighterView = null;
    #commentsHintView: RB.DiffCommentsHintView = null;
    #diffFileIndexView: DiffFileIndexView = null;
    #diffRevisionLabelView: RB.DiffRevisionLabelView = null;
    #diffRevisionSelectorView: RB.DiffRevisionSelectorView = null;
    #paginationView1: RB.PaginationView = null;
    #paginationView2: RB.PaginationView = null;
    #startAtAnchorName: string = null;
    _$anchors: JQuery;
    _commitListView: RB.DiffCommitListView = null;
    _diffReviewableViews: RB.DiffReviewableView[] = [];
    _selectedAnchorIndex = -1;
    router: Router;

    /**
     * Initialize the diff viewer page.
     *
     * Args:
     *     options (ReviewablePageViewOptions):
     *         Options for the view.
     *
     *  See Also:
     *      :js:class:`RB.ReviewablePageView`:
     *          For the option arguments this method takes.
     */
    initialize(options: Partial<ReviewablePageViewOptions>) {
        super.initialize(options);

        this.#$window = $(window);
        this._$anchors = $();

        /*
         * Listen for the construction of added DiffReviewables.
         *
         * We'll queue up the loading and construction of a view when added.
         * This will ultimately result in a RB.DiffReviewableView being
         * constructed, once the data from the server is loaded.
         */
        this.listenTo(this.model.diffReviewables, 'add',
                      this.#onDiffReviewableAdded);

        /*
         * Listen for when we're started and finished populating the list
         * of DiffReviewables. We'll use these events to clear and start the
         * diff loading queue.
         */
        const diffQueue = $.funcQueue('diff_files');

        this.listenTo(this.model.diffReviewables, 'populating', () => {
            this._diffReviewableViews.forEach(view => view.remove());
            this._diffReviewableViews = [];
            this.#diffFileIndexView.clear();
            this.#$diffs.children('.diff-container').remove();
            this.#$highlightedChunk = null;

            diffQueue.clear();
        });
        this.listenTo(this.model.diffReviewables, 'populated',
                      () => diffQueue.start());

        this.router = new Router();
        this.router.route(
            /^(\d+(?:-\d+)?)\/?(\?[^#]*)?/,
            'revision',
            (revision, queryStr) => {
                const queryArgs = Djblets.parseQueryString(queryStr || '');
                const page = queryArgs.page;
                const revisionRange = revision.split('-', 2);

                const interdiffRevision = (revisionRange.length === 2
                                           ? parseInt(revisionRange[1], 10)
                                           : null);

                let baseCommitID = null;
                let tipCommitID = null;

                if (interdiffRevision === null) {
                    baseCommitID = queryArgs['base-commit-id'] || null;
                    tipCommitID = queryArgs['tip-commit-id'] || null;

                    if (baseCommitID !== null) {
                        baseCommitID = parseInt(baseCommitID, 10);
                    }

                    if (tipCommitID !== null) {
                        tipCommitID = parseInt(tipCommitID, 10);
                    }
                }

                this.model.loadDiffRevision({
                    baseCommitID: baseCommitID,
                    filenamePatterns: queryArgs.filenames || null,
                    interdiffRevision: interdiffRevision,
                    page: page ? parseInt(page, 10) : 1,
                    revision: parseInt(revisionRange[0], 10),
                    tipCommitID: tipCommitID,
                });
            });

        /*
         * Begin managing the URL history for the page, so that we can
         * switch revisions and handle pagination while keeping the history
         * clean and the URLs representative of the current state.
         *
         * Note that Backbone will attempt to convert the hash to part of
         * the page URL, stripping away the "#". This will result in a
         * URL pointing to an incorrect, possible non-existent diff revision.
         *
         * We work around that by saving the values for the hash and query
         * string (up above), and by later replacing the current URL with a
         * new one that, amongst other things, contains the hash present
         * when the page was loaded.
         */
        Backbone.history.start({
            hashChange: false,
            pushState: true,
            root: `${this.model.get('reviewRequest').get('reviewURL')}diff/`,
            silent: true,
        });

        this._setInitialURL(document.location.search || '',
                            RB.getLocationHash());
    }

    /**
     * Remove the view from the page.
     *
     * Returns:
     *     DiffViewerPageView:
     *     This object, for chaining.
     */
    remove(): this {
        this.#$window.off(`resize.${this.cid}`);

        if (this.#diffFileIndexView) {
            this.#diffFileIndexView.remove();
        }

        if (this._commitListView) {
            this._commitListView.remove();
        }

        return super.remove();
    }

    /**
     * Render the page and begins loading all diffs.
     *
     * Returns:
     *     RB.DiffViewerPageView:
     *     This instance, for chaining.
     */
    renderPage() {
        super.renderPage();

        const model = this.model;
        const session = UserSession.instance;

        this.#$controls = $('#view_controls');
        console.assert(this.#$controls.length === 1);

        /* Set up the view buttons. */
        this.addViewToggleButton({
            activeDescription: _`
                All lines of the files are being shown. Toggle to
                collapse down to only modified sections instead.
            `,
            activeText: _`Collapse changes`,
            id: 'action-diff-toggle-collapse-changes',
            inactiveDescription: _`
                Only modified sections of the files are being shown. Toggle
                to show all lines instead.
            `,
            inactiveText: _`Expand changes`,
            isActive: !this.model.get('allChunksCollapsed'),
            onToggled: isActive => {
                RB.navigateTo(isActive ? '.?expand=1' : '.?collapse=1');
            },
        });

        if (model.get('canToggleExtraWhitespace')) {
            this.addViewToggleButton({
                activeDescription: _`
                    Mismatched indentation and trailing whitespace are
                    being shown. Toggle to hide instead.
                `,
                activeText: _`Hide extra whitespace`,
                id: 'action-diff-toggle-extra-whitespace',
                inactiveDescription: _`
                    Mismatched indentation and trailing whitespace are
                    being hidden. Toggle to show instead.
                `,
                inactiveText: _`Show extra whitespace`,
                isActive: session.get('diffsShowExtraWhitespace'),
                onToggled: isActive => {
                    session.set('diffsShowExtraWhitespace', isActive);
                },
            });
        }

        this.addViewToggleButton({
            activeDescription: _`
                Sections of the diff containing only whitespace changes are
                being shown. Toggle to hide those instead.
            `,
            activeText: _`Hide whitespace-only changes`,
            id: 'action-diff-toggle-whitespace-only',
            inactiveDescription: _`
                Sections of the diff containing only whitespace changes are
                being hidden. Toggle to show those instead.
            `,
            inactiveText: _`Show whitespace-only changes`,
            isActive: true,
            onToggled: () => {
                this._diffReviewableViews.forEach(
                    view => view.toggleWhitespaceOnlyChunks());
            },
        });

        /* Listen for changes on the commit selector. */
        if (!model.commits.isEmpty()) {
            const commitListModel = new RB.DiffCommitList({
                baseCommitID: model.revision.get('baseCommitID'),
                commits: model.commits,
                historyDiff: model.commitHistoryDiff,
                tipCommitID: model.revision.get('tipCommitID'),
            });

            this.listenTo(
                model.revision,
                'change:baseCommitID change:tipCommitID',
                model => commitListModel.set({
                    baseCommitID: model.get('baseCommitID'),
                    tipCommitID: model.get('tipCommitID'),
                }));

            this.listenTo(
                commitListModel,
                'change:baseCommitID change:tipCommitID',
                this.#onCommitIntervalChanged);

            this._commitListView = new RB.DiffCommitListView({
                el: $('#diff_commit_list').find('.commit-list-container'),
                model: commitListModel,
                showInterCommitDiffControls: true,
            });
            this._commitListView.render();
        }

        this.#diffFileIndexView = new DiffFileIndexView({
            collection: model.files,
            el: $('#diff_index').find('.diff-index-container'),
        });

        this.#diffFileIndexView.render();

        this.listenTo(this.#diffFileIndexView, 'anchorClicked',
                      this.selectAnchorByName);

        this.#diffRevisionLabelView = new RB.DiffRevisionLabelView({
            el: $('#diff_revision_label'),
            model: model.revision,
        });
        this.#diffRevisionLabelView.render();

        this.listenTo(this.#diffRevisionLabelView, 'revisionSelected',
                      this._onRevisionSelected);

        /*
         * Determine whether we need to show the revision selector. If there's
         * only one revision, we don't need to add it.
         */
        const numDiffs = model.get('numDiffs');

        if (numDiffs > 1) {
            this.#diffRevisionSelectorView = new RB.DiffRevisionSelectorView({
                el: $('#diff_revision_selector'),
                model: model.revision,
                numDiffs: numDiffs,
            });
            this.#diffRevisionSelectorView.render();

            this.listenTo(this.#diffRevisionSelectorView, 'revisionSelected',
                          this._onRevisionSelected);
        }

        this.#commentsHintView = new RB.DiffCommentsHintView({
            el: $('#diff_comments_hint'),
            model: model.commentsHint,
        });
        this.#commentsHintView.render();
        this.listenTo(this.#commentsHintView, 'revisionSelected',
                      this._onRevisionSelected);

        this.#paginationView1 = new RB.PaginationView({
            el: $('#pagination1'),
            model: model.pagination,
        });
        this.#paginationView1.render();
        this.listenTo(this.#paginationView1, 'pageSelected',
                      _.partial(this._onPageSelected, false));

        this.#paginationView2 = new RB.PaginationView({
            el: $('#pagination2'),
            model: model.pagination,
        });
        this.#paginationView2.render();
        this.listenTo(this.#paginationView2, 'pageSelected',
                      _.partial(this._onPageSelected, true));

        this.#$diffs = $('#diffs')
            .bindClass(UserSession.instance,
                       'diffsShowExtraWhitespace', 'ewhl');

        this.#chunkHighlighter = new RB.ChunkHighlighterView();
        this.#chunkHighlighter.render().$el.prependTo(this.#$diffs);

        $('#diff-details').removeClass('loading');
        $('#download-diff-action').bindVisibility(model,
                                                  'canDownloadDiff');

        this.#$window.on(`resize.${this.cid}`,
                         _.throttleLayout(this.#onWindowResize.bind(this)));

        /*
         * Begin creating any DiffReviewableViews needed for the page, and
         * start loading their contents.
         */
        if (model.diffReviewables.length > 0) {
            model.diffReviewables.each(
                diffReviewable => this.#onDiffReviewableAdded(diffReviewable));
            $.funcQueue('diff_files').start();
        }
    }

    /**
     * Add a toggle button for changing the view of the diff.
     *
     * Args:
     *     options (ToggleButtonOptions):
     *         The options for the button.
     */
    addViewToggleButton(options: ToggleButtonOptions) {
        console.assert(!!options);

        const $button = $('<button>');
        const updateButton = isActive => {
            let icon;
            let text;
            let description;

            if (isActive) {
                icon = 'fa-minus';
                text = options.activeText;
                description = options.activeDescription;
            } else {
                icon = 'fa-plus';
                text = options.inactiveText;
                description = options.inactiveDescription;
            }

            console.assert(text);
            console.assert(description);

            $button
                .data('is-active', isActive)
                .attr('title', description)
                .html(DiffViewerPageView.viewToggleButtonContentTemplate({
                    iconClass: icon,
                    text: text,
                }));
        };

        updateButton(options.isActive);

        $button
            .attr('id', options.id)
            .on('click', e => {
                e.preventDefault();
                e.stopPropagation();

                const isActive = !$button.data('is-active');

                updateButton(isActive);
                options.onToggled(isActive);
            });

        this.#$controls.append($('<li>').append($button));
    }

    /**
     * Queue the loading of the corresponding diff.
     *
     * When the diff is loaded, it will be placed into the appropriate location
     * in the diff viewer. The anchors on the page will be rebuilt. This will
     * then trigger the loading of the next file.
     *
     * Args:
     *     diffReviewable (RB.DiffReviewable):
     *         The diff reviewable for loading and reviewing the diff.
     *
     *     options (object):
     *         The option arguments that control the behavior of this function.
     *
     * Option Args:
     *     showDeleted (boolean, optional):
     *         Determines whether or not we want to requeue the corresponding
     *         diff in order to show its deleted content.
     */
    queueLoadDiff(
        diffReviewable: RB.DiffReviewable,
        options: {
            showDeleted?: boolean,
        } = {},
    ) {
        $.funcQueue('diff_files').add(async () => {
            const fileDiffID = diffReviewable.get('fileDiffID');

            if (!options.showDeleted && $(`#file${fileDiffID}`).length === 1) {
                /*
                 * We already have this diff (probably pre-loaded), and we
                 * don't want to requeue it to show its deleted content.
                 */
                this.#renderFileDiff(diffReviewable);
            } else {
                /*
                 * We either want to queue this diff for the first time, or we
                 * want to requeue it to show its deleted content.
                 */
                const prefix = (options.showDeleted
                                ? '#file'
                                : '#file_container_');

                const html = await diffReviewable.getRenderedDiff(options);
                const $container = $(prefix + fileDiffID)
                    .parent();

                if ($container.length === 0) {
                    /*
                     * The revision or page may have changed. There's
                     * no element to work with. Just ignore this and
                     * move on to the next.
                     */
                    return;
                }

                $container.hide();

                /*
                 * jQuery's html() and replaceWith() perform checks of
                 * the HTML, looking for things like <script> tags to
                 * determine how best to set the HTML, and possibly
                 * manipulating the string to do some normalization of
                 * for cases we don't need to worry about. While this
                 * is all fine for most HTML fragments, this can be
                 * slow for diffs, given their size, and is
                 * unnecessary. It's much faster to just set innerHTML
                 * directly.
                 */
                $container[0].innerHTML = html;
                this.#renderFileDiff(diffReviewable);
            }
        });
    }

    /**
     * Set up a diff as DiffReviewableView and renders it.
     *
     * This will set up a :js:class:`RB.DiffReviewableView` for the given
     * diffReviewable. The anchors from this diff render will be stored for
     * navigation.
     *
     * Once rendered and set up, the next diff in the load queue will be
     * pulled from the server.
     *
     * Args:
     *     diffReviewable (RB.DiffReviewable):
     *         The reviewable diff to render.
     */
    #renderFileDiff(diffReviewable: RB.DiffReviewable) {
        const elementName = 'file' + diffReviewable.get('fileDiffID');
        const $el = $(`#${elementName}`);

        if ($el.length === 0) {
            /*
             * The user changed revisions before the file finished loading, and
             * the target element no longer exists. Just return.
             */
            $.funcQueue('diff_files').next();

            return;
        }

        /* Check if we're replacing a diff or adding a new one. */
        let isReplacing = true;
        let index = this._diffReviewableViews.findIndex(
            view => (view.model === diffReviewable));

        if (index === -1) {
            index = this._diffReviewableViews.length;
            isReplacing = false;
        }

        const diffReviewableView = new RB.DiffReviewableView({
            el: $el,
            model: diffReviewable,
        });

        if (isReplacing) {
            this._diffReviewableViews.splice(index, 1, diffReviewableView);
        } else {
            this._diffReviewableViews.push(diffReviewableView);
        }

        diffReviewableView.render();
        diffReviewableView.$el.parent().show();

        this.#diffFileIndexView.addDiff(index, diffReviewableView);

        this.listenTo(diffReviewableView, 'fileClicked', () => {
            this.selectAnchorByName(diffReviewable.get('file').get('index'));
        });

        this.listenTo(diffReviewableView, 'chunkClicked', name => {
            this.selectAnchorByName(name, false);
        });

        this.listenTo(diffReviewableView, 'moveFlagClicked', line => {
            this.selectAnchor(this.$(`a[target=${line}]`));
        });

        /* We must rebuild this every time. */
        this._updateAnchors(diffReviewableView.$el);

        this.listenTo(diffReviewableView, 'chunkExpansionChanged', () => {
            /* The selection rectangle may not update -- bug #1353. */
            this.#highlightAnchor(
                $(this._$anchors[this._selectedAnchorIndex]));
        });

        if (this.#startAtAnchorName) {
            /* See if we've loaded the anchor the user wants to start at. */
            let $anchor =
                $(document.getElementsByName(this.#startAtAnchorName));

            /*
             * Some anchors are added by the template (such as those at
             * comment locations), but not all are. If the anchor isn't found,
             * but the URL hash is indicating that we want to start at a
             * location within this file, add the anchor.
             * */
            const urlSplit = this.#startAtAnchorName.split(',');

            if ($anchor.length === 0 &&
                urlSplit.length === 2 &&
                elementName === urlSplit[0]) {
                $anchor = $(DiffViewerPageView.anchorTemplate({
                    anchorName: this.#startAtAnchorName,
                }));

                diffReviewableView.$el
                    .find(`tr[line='${urlSplit[1]}']`)
                        .addClass('highlight-anchor')
                        .append($anchor);
            }

            if ($anchor.length !== 0) {
                this.selectAnchor($anchor);
                this.#startAtAnchorName = null;
            }
        }

        this.listenTo(diffReviewableView, 'showDeletedClicked', () => {
            this.queueLoadDiff(diffReviewable, {showDeleted: true});
            $.funcQueue('diff_files').start();
        });

        $.funcQueue('diff_files').next();
    }

    /**
     * Select the anchor at a specified location.
     *
     * By default, this will scroll the page to position the anchor near
     * the top of the view.
     *
     * Args:
     *     $anchor (jQuery):
     *         The anchor to select.
     *
     *     scroll (boolean, optional):
     *         Whether to scroll the page to the anchor. This defaults to
     *         ``true``.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the anchor was found and selected. ``false`` if not
     *     found.
     */
    selectAnchor(
        $anchor: JQuery,
        scroll?: boolean,
    ): boolean {
        if (!$anchor || $anchor.length === 0 ||
            $anchor.parent().is(':hidden')) {
            return false;
        }

        if (scroll !== false) {
            this._navigate({
                anchor: $anchor.attr('name'),
                updateURLOnly: true,
            });

            const anchorOffset = $anchor.offset().top;
            let scrollAmount = 0;

            if (this.unifiedBanner) {
                /*
                 * The scroll offset calculation when we're running with the
                 * unified banner is somewhat complex because the height of the
                 * banner isn't static. The file index gets docked into the
                 * banner, and changes its height depending on what files are
                 * shown in the viewport.
                 *
                 * In order to try to scroll to the position where the top of
                 * the file is nicely visible, we end up doing this twice.
                 * First we try to determine a scroll offset based on the
                 * position of the anchor. We then rerun the calculation using
                 * the new offset to dial in closer to the right place.
                 *
                 * This still may not be perfect, especially when file borders
                 * are close to the boundary where they're scrolling on or off
                 * the screen, but it generally seems to do pretty well.
                 */
                const newOffset = this.#computeScrollHeight(
                    anchorOffset - DiffViewerPageView.DIFF_SCROLLDOWN_AMOUNT);
                scrollAmount = this.#computeScrollHeight(
                    anchorOffset - newOffset);

            } else if (RB.DraftReviewBannerView.instance) {
                scrollAmount = (DiffViewerPageView.DIFF_SCROLLDOWN_AMOUNT +
                                RB.DraftReviewBannerView.instance.getHeight());
            }

            this.#$window.scrollTop(anchorOffset - scrollAmount);
        }

        this.#highlightAnchor($anchor);

        for (let i = 0; i < this._$anchors.length; i++) {
            if (this._$anchors[i] === $anchor[0]) {
                this._selectedAnchorIndex = i;
                break;
            }
        }

        return true;
    }

    /**
     * Compute the ideal scroll offset based on the unified banner.
     *
     * This attempts to find the ideal scroll offset based on what the diff
     * file index is doing within the unified banner.
     *
     * Args:
     *     startingOffset (number):
     *         The target scroll offset.
     *
     * Returns:
     *     number:
     *     The number of pixels to adjust the starting offset by in order to
     *     maximize the likelihood of the anchor appearing at the top of the
     *     visible viewport.
     */
    #computeScrollHeight(startingOffset: number): number {
        const $window = $(window);
        const bannerHeight = this.unifiedBanner.getHeight(false);

        const newDockHeight = this.#diffFileIndexView.getDockedIndexExtents(
            startingOffset + bannerHeight,
            startingOffset + $window.height() - bannerHeight).height;

        return (bannerHeight + newDockHeight + 20 +
                DiffViewerPageView.DIFF_SCROLLDOWN_AMOUNT);
    }

    /**
     * Select an anchor by name.
     *
     * Args:
     *     name (string):
     *         The name of the anchor.
     *
     *     scroll (boolean, optional):
     *         Whether to scroll the page to the anchor. This defaults to
     *         ``true``.
     *
     * Returns:
     *     boolean:
     *     ``true`` if the anchor was found and selected. ``false`` if not
     *     found.
     */
    selectAnchorByName(
        name: string,
        scroll?: boolean,
    ): boolean {
        return this.selectAnchor($(document.getElementsByName(name)), scroll);
    }

    /**
     * Highlight a chunk bound to an anchor element.
     *
     * Args:
     *     $anchor (jQuery):
     *         The anchor to highlight.
     */
    #highlightAnchor($anchor: JQuery) {
        this.#$highlightedChunk =
            $anchor.closest('tbody')
            .add($anchor.closest('thead'));
        this.#chunkHighlighter.highlight(this.#$highlightedChunk);
    }

    /**
     * Update the list of known anchors.
     *
     * This will update the list of known anchors based on all named anchors
     * in the specified table. This is called after every part of the diff
     * that is loaded.
     *
     * If no anchor is selected, this will try to select the first one.
     *
     * Args:
     *     $table (jQuery):
     *         The table containing anchors.
     */
    _updateAnchors($table: JQuery) {
        this._$anchors = this._$anchors.add($table.find('th a[name]'));

        /* Skip over the change index to the first item. */
        if (this._selectedAnchorIndex === -1 && this._$anchors.length > 0) {
            this._selectedAnchorIndex = 0;
            this.#highlightAnchor(
                $(this._$anchors[this._selectedAnchorIndex]));
        }
    }

    /**
     * Return the next navigatable anchor.
     *
     * This will take a direction to search, starting at the currently
     * selected anchor. The next anchor matching one of the types in the
     * anchorTypes bitmask will be returned. If no anchor is found,
     * null will be returned.
     *
     * Args:
     *     dir (number):
     *         The direction to navigate in. This should be
     *         :js:data:`SCROLL_BACKWARD` or js:data:`SCROLL_FORWARD`.
     *
     *     anchorTypes (number):
     *         A bitmask of types to consider when searching for the next
     *         anchor.
     *
     * Returns:
     *     jQuery:
     *     The anchor, if found. If an anchor was not found, ``null`` is
     *     returned.
     */
    #getNextAnchor(
        dir: number,
        anchorTypes: number,
    ): JQuery {
        for (let i = this._selectedAnchorIndex + dir;
             i >= 0 && i < this._$anchors.length;
             i += dir) {
            const $anchor = $(this._$anchors[i]);

            if ($anchor.closest('tr').hasClass('dimmed')) {
                continue;
            }

            if (((anchorTypes & DiffViewerPageView.ANCHOR_COMMENT) &&
                 $anchor.hasClass('commentflag-anchor')) ||
                ((anchorTypes & DiffViewerPageView.ANCHOR_FILE) &&
                 $anchor.hasClass('file-anchor')) ||
                ((anchorTypes & DiffViewerPageView.ANCHOR_CHUNK) &&
                 $anchor.hasClass('chunk-anchor'))) {
                return $anchor;
            }
        }

        return null;
    }

    /**
     * Select the previous file's header on the page.
     */
    private _selectPreviousFile() {
        this.selectAnchor(
            this.#getNextAnchor(DiffViewerPageView.SCROLL_BACKWARD,
                                DiffViewerPageView.ANCHOR_FILE));
    }

    /**
     * Select the next file's header on the page.
     */
    private _selectNextFile() {
        this.selectAnchor(
            this.#getNextAnchor(DiffViewerPageView.SCROLL_FORWARD,
                                DiffViewerPageView.ANCHOR_FILE));
    }

    /**
     * Select the previous diff chunk on the page.
     */
    private _selectPreviousDiff() {
        this.selectAnchor(
            this.#getNextAnchor(DiffViewerPageView.SCROLL_BACKWARD,
                                (DiffViewerPageView.ANCHOR_CHUNK |
                                 DiffViewerPageView.ANCHOR_FILE)));
    }

    /**
     * Select the next diff chunk on the page.
     */
    private _selectNextDiff() {
        this.selectAnchor(
            this.#getNextAnchor(DiffViewerPageView.SCROLL_FORWARD,
                                (DiffViewerPageView.ANCHOR_CHUNK |
                                 DiffViewerPageView.ANCHOR_FILE)));
    }

    /**
     * Select the previous comment on the page.
     */
    private _selectPreviousComment() {
        this.selectAnchor(
            this.#getNextAnchor(DiffViewerPageView.SCROLL_BACKWARD,
                                DiffViewerPageView.ANCHOR_COMMENT));
    }

    /**
     * Select the next comment on the page.
     */
    private _selectNextComment() {
        this.selectAnchor(
            this.#getNextAnchor(DiffViewerPageView.SCROLL_FORWARD,
                                DiffViewerPageView.ANCHOR_COMMENT));
    }

    /**
     * Re-center the currently selected area on the page.
     */
    private _recenterSelected() {
        this.selectAnchor($(this._$anchors[this._selectedAnchorIndex]));
    }

    /**
     * Create a comment for a chunk of a diff
     */
    private _createComment() {
        const chunkID = this.#$highlightedChunk[0].id;
        const chunkElement = document.getElementById(chunkID);

        if (chunkElement) {
            const lineElements = chunkElement.getElementsByTagName('tr');
            const beginLineNum = lineElements[0].getAttribute('line');
            const beginNode = lineElements[0].cells[2];
            const endLineNum = lineElements[lineElements.length - 1]
                .getAttribute('line');
            const endNode = lineElements[lineElements.length - 1].cells[2];

            this._diffReviewableViews.forEach(diffReviewableView => {
                if ($.contains(diffReviewableView.el, beginNode)){
                    diffReviewableView.createComment(beginLineNum, endLineNum,
                                                     beginNode, endNode);
                }
            });
        }
    }

    /**
     * Set the initial URL for the page.
     *
     * This accomplishes two things:
     *
     * 1. The user may have viewed ``diff/``, and not ``diff/<revision>/``,
     *    but we want to always show the revision in the URL. This ensures
     *    we have a URL equivalent to the one we get when clicking a revision
     *    in the slider.
     *
     * 2. We want to add back any hash and query string that may have been
     *    stripped away, so the URL doesn't appear to suddenly change from
     *    what the user expected.
     *
     * This won't invoke any routes or store any new history. The back button
     * will correctly bring the user to the previous page.
     *
     * Args:
     *     queryString (string):
     *         The query string provided in the URL.
     *
     *     anchor (string):
     *         The anchor provided in the URL.
     */
    _setInitialURL(
        queryString: string,
        anchor: string,
    ) {
        this.#startAtAnchorName = anchor || null;

        this._navigate({
            anchor: anchor,
            queryString: queryString,
            updateURLOnly: true,
        });
    }

    /**
     * Navigate to a new page state by calculating and setting a URL.
     *
     * This builds a URL consisting of the revision range and any other
     * state that impacts the view of the page (page number and filtered list
     * of filename patterns), updating the current location in the browser and
     * (by default) triggering a route change.
     *
     * Args:
     *     options (object):
     *         The options for the navigation.
     *
     * Option Args:
     *     revision (number, optional):
     *         The revision (or first part of an interdiff range) to view.
     *         Defaults to the current revision.
     *
     *     interdiffRevision (number, optional):
     *         The second revision of an interdiff range to view.
     *         Defaults to the current revision for the interdiff, if any.
     *
     *     page (number, optional):
     *         A page number to specify. If not provided, and if the revision
     *         range has not changed, the existing value (or lack of one)
     *         in the URL will be used. If the revision range has changed and
     *         a value was not explicitly provided, a ``page=`` will not be
     *         added to the URL.
     *
     *     anchor (string, optional):
     *         An anchor name to navigate to. This cannot begin with ``#``.
     *
     *     queryString (string, optional):
     *         An explicit query string to use for the URL. If specified,
     *         a query string will not be computed. This must begin with ``?``.
     *
     *     updateURLOnly (boolean, optional):
     *         If ``true``, the location in the browser will be updated, but
     *         a route will not be triggered.
     *
     *     baseCommitID (string, optional):
     *         The ID of the base commit to use in the request.
     *
     *     tipCommitID (string, optional):
     *         The ID of the top commit to use in the request.
     */
    _navigate(options: {
        revision?: number,
        interdiffRevision?: number,
        page?: number,
        anchor?: string,
        queryString?: string,
        updateURLOnly?: boolean,
        baseCommitID?: string,
        tipCommitID?: string,
    }) {
        const curRevision = this.model.revision.get('revision');
        const curInterdiffRevision =
            this.model.revision.get('interdiffRevision');

        /* Start the URL off with the revision range. */
        const revision = (options.revision !== undefined
                          ? options.revision
                          : curRevision);
        const interdiffRevision = (options.interdiffRevision !== undefined
                                   ? options.interdiffRevision
                                   : curInterdiffRevision);

        let baseURL = revision;

        if (interdiffRevision) {
            baseURL += `-${interdiffRevision}`;
        }

        baseURL += '/';

        /*
         * If an explicit query string is provided, we'll just use that.
         * Otherwise, we'll generate one.
         */
        type QueryData = string | {
            name: string,
            value: any,
        }[];
        let queryData: QueryData = options.queryString;

        if (queryData === undefined) {
            /*
            * We'll build as an array to maintain a specific order, which
            * helps with caching and testing.
            */
            queryData = [];

            /*
             * We want to be smart about when we include ?page=. We always
             * include it if it's explicitly specified in options. If it's
             * not, then we'll fall back to what's currently in the URL, but
             * only if the revision range is staying the same, otherwise we're
             * taking it out. This simulates the behavior we've always had.
             */
            let page = options.page;

            if (page === undefined &&
                revision === curRevision &&
                interdiffRevision === curInterdiffRevision) {
                /*
                 * It's the same, so we can plug in the page from the
                 * current URL.
                 */
                page = this.model.pagination.get('currentPage');
            }

            if (page && page !== 1) {
                queryData.push({
                    name: 'page',
                    value: page,
                });
            }

            if (options.baseCommitID) {
                queryData.push({
                    name: 'base-commit-id',
                    value: options.baseCommitID,
                });
            }

            if (options.tipCommitID) {
                queryData.push({
                    name: 'tip-commit-id',
                    value: options.tipCommitID,
                });
            }

            const filenamePatterns = this.model.get('filenamePatterns');

            if (filenamePatterns && filenamePatterns.length > 0) {
                queryData.push({
                    name: 'filenames',
                    value: filenamePatterns,
                });
            }
        }

        const url = Djblets.buildURL({
            anchor: options.anchor,
            baseURL: baseURL,
            queryData: queryData,
        });

        /*
         * Determine if we're performing the navigation or just updating the
         * displayed URL.
         */
        let navOptions;

        if (options.updateURLOnly) {
            navOptions = {
                replace: true,
                trigger: false,
            };
        } else {
            navOptions = {
                trigger: true,
            };
        }

        this.router.navigate(url, navOptions);
    }

    /**
     * Handler for when a RB.DiffReviewable is added.
     *
     * This will add a placeholder entry for the file and queue the diff
     * for loading/rendering.
     *
     * Args:
     *     diffReviewable (RB.DiffReviewable):
     *         The DiffReviewable that was added.
     */
    #onDiffReviewableAdded(diffReviewable: RB.DiffReviewable) {
        const file = diffReviewable.get('file');

        this.#$diffs.append(DiffViewerPageView.fileEntryTemplate({
            filename: file.get('depotFilename'),
            id: file.id,
            newFile: file.get('isnew'),
        }));

        this.queueLoadDiff(diffReviewable);
    }

    /**
     * Handler for when the window resizes.
     *
     * Triggers a relayout of all the diffs and the chunk highlighter.
     */
    #onWindowResize() {
        for (let i = 0; i < this._diffReviewableViews.length; i++) {
            this._diffReviewableViews[i].updateLayout();
        }

        this.#chunkHighlighter.updateLayout();

        if (this.unifiedBanner) {
            this.#diffFileIndexView.queueUpdateLayout();
        }
    }

    /**
     * Callback for when a new revision is selected.
     *
     * This supports both single revisions and interdiffs. If `base` is 0, a
     * single revision is selected. If not, the interdiff between `base` and
     * `tip` will be shown.
     *
     * This will always implicitly navigate to page 1 of any paginated diffs.
     *
     * Args:
     *     revisions (Array of number):
     *         The revision range to show.
     */
    _onRevisionSelected(revisions: number[]) {
        let base = revisions[0];
        let tip = revisions[1];

        if (base === 0) {
            /* This is a single revision, not an interdiff. */
            base = tip;
            tip = null;
        }

        this._navigate({
            interdiffRevision: tip,
            revision: base,
        });
    }

    /**
     * Callback for when a new page is selected.
     *
     * Navigates to the same revision with a different page number.
     *
     * Args:
     *     scroll (boolean):
     *         Whether to scroll to the file index.
     *
     *     page (number):
     *         The page number to navigate to.
     */
    _onPageSelected(
        scroll: boolean,
        page: number,
    ) {
        if (scroll) {
            this.selectAnchorByName('index_header', true);
        }

        this._navigate({
            page: page,
        });
    }

    /**
     * Handle the selected commit interval changing.
     *
     * This will navigate to a diff with the selected base and tip commit IDs.
     *
     * Args:
     *     model (RB.DiffCommitList):
     *          The model that changed.
     */
    #onCommitIntervalChanged(model: RB.DiffCommitList) {
        this._navigate({
            baseCommitID: model.get('baseCommitID'),
            tipCommitID: model.get('tipCommitID'),
        });
    }
}
