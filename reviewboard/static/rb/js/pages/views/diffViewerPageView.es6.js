/**
 * Manages the diff viewer page.
 *
 * This provides functionality for the diff viewer page for managing the
 * loading and display of diffs, and all navigation around the diffs.
 */
RB.DiffViewerPageView = RB.ReviewablePageView.extend({
    SCROLL_BACKWARD: -1,
    SCROLL_FORWARD: 1,

    ANCHOR_COMMENT: 1,
    ANCHOR_FILE: 2,
    ANCHOR_CHUNK: 4,

    DIFF_SCROLLDOWN_AMOUNT: 15,

    keyBindings: {
        'aAKP<m': '_selectPreviousFile',
        'fFJN>': '_selectNextFile',
        'sSkp,': '_selectPreviousDiff',
        'dDjn.': '_selectNextDiff',
        '[x': '_selectPreviousComment',
        ']c': '_selectNextComment',
        '\x0d': '_recenterSelected',
        'rR': '_createComment',
    },

    events: _.extend({
        'click .toggle-whitespace-only-chunks': '_toggleWhitespaceOnlyChunks',
        'click .toggle-show-whitespace': '_toggleShowExtraWhitespace',
    }, RB.ReviewablePageView.prototype.events),

    _fileEntryTemplate: _.template(dedent`
        <div class="diff-container">
         <div class="diff-box">
          <table class="sidebyside loading <% if (newFile) { %>newfile<% } %>"
                 id="file_container_<%- id %>">
           <thead>
            <tr class="filename-row">
             <th>
              <span class="fa fa-spinner fa-pulse"></span>
              <%- filename %>
             </th>
            </tr>
           </thead>
          </table>
         </div>
        </div>
    `),

    /* Template for code line link anchor */
    anchorTemplate: _.template(
        '<a name="<%- anchorName %>" class="highlight-anchor"></a>'),

    /**
     * Initialize the diff viewer page.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     *  See Also:
     *      :js:class:`RB.ReviewablePageView`:
     *          For the option arguments this method takes.
     */
    initialize(options) {
        RB.ReviewablePageView.prototype.initialize.call(this, options);

        this._selectedAnchorIndex = -1;
        this._$window = $(window);
        this._$anchors = $();
        this._$controls = null;
        this._$diffs = null;
        this._diffReviewableViews = [];
        this._diffFileIndexView = null;
        this._highlightedChunk = null;
        this._commitListView = null;

        /*
         * Listen for the construction of added DiffReviewables.
         *
         * We'll queue up the loading and construction of a view when added.
         * This will ultimately result in a RB.DiffReviewableView being
         * constructed, once the data from the server is loaded.
         */
        this.listenTo(this.model.diffReviewables, 'add',
                      this._onDiffReviewableAdded);

        /*
         * Listen for when we're started and finished populating the list
         * of DiffReviewables. We'll use these events to clear and start the
         * diff loading queue.
         */
        const diffQueue = $.funcQueue('diff_files');

        this.listenTo(this.model.diffReviewables, 'populating', () => {
            this._diffReviewableViews.forEach(view => view.remove());
            this._diffReviewableViews = [];
            this._$diffs.children('.diff-container').remove();
            this._highlightedChunk = null;

            diffQueue.clear();
        });
        this.listenTo(this.model.diffReviewables, 'populated',
                      () => diffQueue.start());

        this.router = new Backbone.Router();
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
                    page: page ? parseInt(page, 10) : 1,
                    filenamePatterns: queryArgs.filenames || null,
                    revision: parseInt(revisionRange[0], 10),
                    interdiffRevision: interdiffRevision,
                    baseCommitID: baseCommitID,
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
            pushState: true,
            hashChange: false,
            root: `${this.model.get('reviewRequest').get('reviewURL')}diff/`,
            silent: true,
        });

        this._setInitialURL(document.location.search || '',
                            RB.getLocationHash());
    },

    /**
     * Remove the view from the page.
     */
    remove() {
        RB.ReviewablePageView.prototype.remove.call(this);

        this._$window.off(`resize.${this.cid}`);
        this._diffFileIndexView.remove();

        if (this._commitListView) {
            this._commitListView.remove();
        }
    },

    /**
     * Render the page and begins loading all diffs.
     *
     * Returns:
     *     RB.DiffViewerPageView:
     *     This instance, for chaining.
     */
    render() {
        RB.ReviewablePageView.prototype.render.call(this);

        this._$controls = $('#view_controls');

        if (!this.model.commits.isEmpty()) {
            const commitListModel = new RB.DiffCommitList({
                commits: this.model.commits,
                historyDiff: this.model.commitHistoryDiff,
                baseCommitID: this.model.revision.get('baseCommitID'),
                tipCommitID: this.model.revision.get('tipCommitID'),
            });

            this.listenTo(
                this.model.revision,
                'change:baseCommitID change:tipCommitID',
                model => commitListModel.set({
                    baseCommitID: model.get('baseCommitID'),
                    tipCommitID: model.get('tipCommitID'),
                }));

            this.listenTo(
                commitListModel,
                'change:baseCommitID change:tipCommitID',
                this._onCommitIntervalChanged);

            this._commitListView = new RB.DiffCommitListView({
                el: $('#diff_commit_list').find('.commit-list-container'),
                model: commitListModel,
                showInterCommitDiffControls: true,
            });
            this._commitListView.render();
        }

        this._diffFileIndexView = new RB.DiffFileIndexView({
            el: $('#diff_index').find('.diff-index-container'),
            collection: this.model.files,
        });

        this._diffFileIndexView.render();

        this.listenTo(this._diffFileIndexView, 'anchorClicked',
                      this.selectAnchorByName);

        this._diffRevisionLabelView = new RB.DiffRevisionLabelView({
            el: $('#diff_revision_label'),
            model: this.model.revision,
        });
        this._diffRevisionLabelView.render();

        this.listenTo(this._diffRevisionLabelView, 'revisionSelected',
                      this._onRevisionSelected);

        /*
         * Determine whether we need to show the revision selector. If there's
         * only one revision, we don't need to add it.
         */
        const numDiffs = this.model.get('numDiffs');

        if (numDiffs > 1) {
            this._diffRevisionSelectorView = new RB.DiffRevisionSelectorView({
                el: $('#diff_revision_selector'),
                model: this.model.revision,
                numDiffs: numDiffs,
            });
            this._diffRevisionSelectorView.render();

            this.listenTo(this._diffRevisionSelectorView, 'revisionSelected',
                          this._onRevisionSelected);
        }

        this._commentsHintView = new RB.DiffCommentsHintView({
            el: $('#diff_comments_hint'),
            model: this.model.commentsHint,
        });
        this._commentsHintView.render();
        this.listenTo(this._commentsHintView, 'revisionSelected',
                      this._onRevisionSelected);

        this._paginationView1 = new RB.PaginationView({
            el: $('#pagination1'),
            model: this.model.pagination,
        });
        this._paginationView1.render();
        this.listenTo(this._paginationView1, 'pageSelected',
                      _.partial(this._onPageSelected, false));

        this._paginationView2 = new RB.PaginationView({
            el: $('#pagination2'),
            model: this.model.pagination,
        });
        this._paginationView2.render();
        this.listenTo(this._paginationView2, 'pageSelected',
                      _.partial(this._onPageSelected, true));

        this._$diffs = $('#diffs')
            .bindClass(RB.UserSession.instance,
                       'diffsShowExtraWhitespace', 'ewhl');

        this._chunkHighlighter = new RB.ChunkHighlighterView();
        this._chunkHighlighter.render().$el.prependTo(this._$diffs);

        $('#diff-details').removeClass('loading');
        $('#download-diff-action').bindVisibility(this.model,
                                                  'canDownloadDiff');

        this._$window.on(`resize.${this.cid}`,
                         _.throttleLayout(this._onWindowResize.bind(this)));

        /*
         * Begin creating any DiffReviewableViews needed for the page, and
         * start loading their contents.
         */
        if (this.model.diffReviewables.length > 0) {
            this.model.diffReviewables.each(
                diffReviewable => this._onDiffReviewableAdded(diffReviewable));
            $.funcQueue('diff_files').start();
        }

        return this;
    },

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
     *     showDeleted (boolean):
     *         Determines whether or not we want to requeue the corresponding
     *         diff in order to show its deleted content.
     */
    queueLoadDiff(diffReviewable, options={}) {
        $.funcQueue('diff_files').add(() => {
            const fileDiffID = diffReviewable.get('fileDiffID');

            if (!options.showDeleted && $(`#file${fileDiffID}`).length === 1) {
                /*
                 * We already have this diff (probably pre-loaded), and we
                 * don't want to requeue it to show its deleted content.
                 */
                this._renderFileDiff(diffReviewable);
            } else {
                /*
                 * We either want to queue this diff for the first time, or we
                 * want to requeue it to show its deleted content.
                 */
                const prefix = (options.showDeleted
                                ? '#file'
                                : '#file_container_');

                diffReviewable.getRenderedDiff({
                    complete: xhr => {
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
                        $container[0].innerHTML = xhr.responseText;
                        this._renderFileDiff(diffReviewable);
                    }
                }, this, options);
            }
        });
    },

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
    _renderFileDiff(diffReviewable) {
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

        const diffReviewableView = new RB.DiffReviewableView({
            el: $el,
            model: diffReviewable,
        });

        this._diffFileIndexView.addDiff(this._diffReviewableViews.length,
                                        diffReviewableView);

        this._diffReviewableViews.push(diffReviewableView);
        diffReviewableView.render();
        diffReviewableView.$el.parent().show();

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
            this._highlightAnchor(
                $(this._$anchors[this._selectedAnchorIndex]));
        });

        if (this._startAtAnchorName) {
            /* See if we've loaded the anchor the user wants to start at. */
            let $anchor =
                $(document.getElementsByName(this._startAtAnchorName));

            /*
             * Some anchors are added by the template (such as those at
             * comment locations), but not all are. If the anchor isn't found,
             * but the URL hash is indicating that we want to start at a
             * location within this file, add the anchor.
             * */
            const urlSplit = this._startAtAnchorName.split(',');

            if ($anchor.length === 0 &&
                urlSplit.length === 2 &&
                elementName === urlSplit[0]) {
                $anchor = $(this.anchorTemplate({
                    anchorName: this._startAtAnchorName,
                }));

                diffReviewableView.$el
                    .find(`tr[line='${urlSplit[1]}']`)
                        .addClass('highlight-anchor')
                        .append($anchor);
            }

            if ($anchor.length !== 0) {
                this.selectAnchor($anchor);
                this._startAtAnchorName = null;
            }
        }

        this.listenTo(diffReviewableView, 'showDeletedClicked', () => {
            this.queueLoadDiff(diffReviewable, {showDeleted: true});
            $.funcQueue('diff_files').start();
        });

        $.funcQueue('diff_files').next();
    },

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
    selectAnchor($anchor, scroll) {
        if (!$anchor || $anchor.length === 0 ||
            $anchor.parent().is(':hidden')) {
            return false;
        }

        if (scroll !== false) {
            this._navigate({
                anchor: $anchor.attr('name'),
                updateURLOnly: true,
            });

            let scrollAmount = this.DIFF_SCROLLDOWN_AMOUNT;

            if (RB.DraftReviewBannerView.instance) {
                scrollAmount += RB.DraftReviewBannerView.instance.getHeight();
            }

            this._$window.scrollTop($anchor.offset().top - scrollAmount);
        }

        this._highlightAnchor($anchor);

        for (let i = 0; i < this._$anchors.length; i++) {
            if (this._$anchors[i] === $anchor[0]) {
                this._selectedAnchorIndex = i;
                break;
            }
        }

        return true;
    },

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
    selectAnchorByName(name, scroll) {
        return this.selectAnchor($(document.getElementsByName(name)), scroll);
    },

    /**
     * Highlight a chunk bound to an anchor element.
     *
     * Args:
     *     $anchor (jQuery):
     *         The anchor to highlight.
     */
    _highlightAnchor($anchor) {
        this._highlightedChunk =
            $anchor.closest('tbody')
            .add($anchor.closest('thead'));
        this._chunkHighlighter.highlight(this._highlightedChunk);
    },

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
    _updateAnchors($table) {
        this._$anchors = this._$anchors.add($table.find('th a[name]'));

        /* Skip over the change index to the first item. */
        if (this._selectedAnchorIndex === -1 && this._$anchors.length > 0) {
            this._selectedAnchorIndex = 0;
            this._highlightAnchor(
                $(this._$anchors[this._selectedAnchorIndex]));
        }
    },

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
    _getNextAnchor(dir, anchorTypes) {
        for (let i = this._selectedAnchorIndex + dir;
             i >= 0 && i < this._$anchors.length;
             i += dir) {
            const $anchor = $(this._$anchors[i]);

            if ($anchor.closest('tr').hasClass('dimmed')) {
                continue;
            }

            if (((anchorTypes & this.ANCHOR_COMMENT) &&
                 $anchor.hasClass('commentflag-anchor')) ||
                ((anchorTypes & this.ANCHOR_FILE) &&
                 $anchor.hasClass('file-anchor')) ||
                ((anchorTypes & this.ANCHOR_CHUNK) &&
                 $anchor.hasClass('chunk-anchor'))) {
                return $anchor;
            }
        }

        return null;
    },

    /**
     * Select the previous file's header on the page.
     */
    _selectPreviousFile() {
        this.selectAnchor(this._getNextAnchor(this.SCROLL_BACKWARD,
                                              this.ANCHOR_FILE));
    },

    /**
     * Select the next file's header on the page.
     */
    _selectNextFile() {
        this.selectAnchor(this._getNextAnchor(this.SCROLL_FORWARD,
                                              this.ANCHOR_FILE));
    },

    /**
     * Select the previous diff chunk on the page.
     */
    _selectPreviousDiff() {
        this.selectAnchor(
            this._getNextAnchor(this.SCROLL_BACKWARD,
                                this.ANCHOR_CHUNK | this.ANCHOR_FILE));
    },

    /**
     * Select the next diff chunk on the page.
     */
    _selectNextDiff() {
        this.selectAnchor(
            this._getNextAnchor(this.SCROLL_FORWARD,
                                this.ANCHOR_CHUNK | this.ANCHOR_FILE));
    },

    /**
     * Select the previous comment on the page.
     */
    _selectPreviousComment() {
        this.selectAnchor(
            this._getNextAnchor(this.SCROLL_BACKWARD, this.ANCHOR_COMMENT));
    },

    /**
     * Select the next comment on the page.
     */
    _selectNextComment() {
        this.selectAnchor(
            this._getNextAnchor(this.SCROLL_FORWARD, this.ANCHOR_COMMENT));
    },

    /**
     * Re-center the currently selected area on the page.
     */
    _recenterSelected() {
        this.selectAnchor($(this._$anchors[this._selectedAnchorIndex]));
    },

   /**
    * Create a comment for a chunk of a diff
    */
    _createComment() {
        const chunkID = this._highlightedChunk[0].id;
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
    },

    /**
     * Toggle the display of diff chunks that only contain whitespace changes.
     *
     * Returns:
     *     boolean:
     *     ``false``, to prevent events from bubbling up.
     */
    _toggleWhitespaceOnlyChunks() {
        this._diffReviewableViews.forEach(
            view => view.toggleWhitespaceOnlyChunks());

        this._$controls.find('.ws').toggle();

        return false;
    },

    /**
     * Toggle the display of extra whitespace highlights on diffs.
     *
     * A cookie will be set to the new whitespace display setting, so that
     * the new option will be the default when viewing diffs.
     *
     * Returns:
     *     boolean:
     *     ``false``, to prevent events from bubbling up.
     */
    _toggleShowExtraWhitespace() {
        this._$controls.find('.ew').toggle();
        RB.UserSession.instance.toggleAttr('diffsShowExtraWhitespace');

        return false;
    },

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
    _setInitialURL(queryString, anchor) {
        this._startAtAnchorName = anchor || null;

        this._navigate({
            queryString: queryString,
            anchor: anchor,
            updateURLOnly: true,
        });
    },

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
    _navigate(options) {
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
        let queryData = options.queryString;

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
            baseURL: baseURL,
            queryData: queryData,
            anchor: options.anchor,
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
    },

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
    _onDiffReviewableAdded(diffReviewable) {
        const file = diffReviewable.get('file');

        this._$diffs.append(this._fileEntryTemplate({
            id: file.id,
            newFile: file.get('isnew'),
            filename: file.get('depotFilename'),
        }));

        this.queueLoadDiff(diffReviewable);
    },

    /**
     * Handler for when the window resizes.
     *
     * Triggers a relayout of all the diffs and the chunk highlighter.
     */
    _onWindowResize() {
        for (let i = 0; i < this._diffReviewableViews.length; i++) {
            this._diffReviewableViews[i].updateLayout();
        }

        this._chunkHighlighter.updateLayout();
    },

    /**
     * Callback for when a new revision is selected.
     *
     * This supports both single revisions and interdiffs. If `base` is 0, a
     * single revision is selected. If not, the interdiff between `base` and
     * `tip` will be shown.
     *
     * This will always implicitly navigate to page 1 of any paginated diffs.
     */
    _onRevisionSelected(revisions) {
        let base = revisions[0];
        let tip = revisions[1];

        if (base === 0) {
            /* This is a single revision, not an interdiff. */
            base = tip;
            tip = null;
        }

        this._navigate({
            revision: base,
            interdiffRevision: tip,
        });
    },

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
    _onPageSelected(scroll, page) {
        if (scroll) {
            this.selectAnchorByName('index_header', true);
        }

        this._navigate({
            page: page,
        });
    },

    /**
     * Handle the selected commit interval changing.
     *
     * This will navigate to a diff with the selected base and tip commit IDs.
     *
     * Args:
     *     model (RB.DiffCommitList):
     *          The model that changed.
     */
    _onCommitIntervalChanged(model) {
        this._navigate({
            baseCommitID: model.get('baseCommitID'),
            tipCommitID: model.get('tipCommitID'),
        });
    },
});
_.extend(RB.DiffViewerPageView.prototype, RB.KeyBindingsMixin);
