/*
 * Queues loading of diff fragments from a page.
 *
 * This is used to load diff fragments one-by-one, and to intelligently
 * batch the loads to only fetch at most one set of fragments per file.
 */
RB.DiffFragmentQueueView = Backbone.View.extend({
    events: {
        'click .diff-expand-btn': '_onExpandButtonClicked',
        'click .diff-collapse-btn': '_onCollapseButtonClicked'
    },

    // The timeout for a mouseout event to fire after it actually occurs.
    _timeout: 250,

    COLLAPSED_HEADERS_HEIGHT: 4,

    initialize: function() {
        this._queue = {};
        this._saved = {};

        this._centered = new RB.CenteredElementManager();

        _.bindAll(this,
                  '_onExpandOrCollapseFinished',
                  '_tryHideControlsDelayed',
                  '_tryShowControlsDelayed');
    },

    /*
     * Queues the load of a diff fragment from the server.
     *
     * This will be added to a list, which will fetch the comments in batches
     * based on file IDs.
     */
    queueLoad: function(commentID, key) {
        var queue = this._queue;

        if (!queue[key]) {
            queue[key] = [];
        }

        queue[key].push(commentID);
    },

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
    saveFragment(commentID) {
        const $el = this._getCommentContainer(commentID);

        if ($el.length === 1 && $el.data('diff-fragment-loaded')) {
            this._saved[commentID] = $el.html();
        }
    },

    /*
     * Begins the loading of all diff fragments on the page belonging to
     * the specified queue.
     */
    loadFragments: function() {
        var queueName = this.options.queueName,
            urlPrefix,
            urlSuffix;

        if (_.isEmpty(this._queue) && _.isEmpty(this._saved)) {
            return;
        }

        urlPrefix = this.options.reviewRequestPath +
                    'fragments/diff-comments/';
        urlSuffix = '/?queue=' + queueName +
                    '&container_prefix=' + this.options.containerPrefix +
                    '&' + TEMPLATE_SERIAL;

        _.each(this._queue, commentIDs => {
            $.funcQueue(queueName).add(() => {
                const pendingCommentIDs = [];

                /*
                 * Check if there are any comment IDs that have been saved.
                 * We don't need to reload these from the server.
                 */
                for (let i = 0; i < commentIDs.length; i++) {
                    const commentID = commentIDs[i];

                    if (this._saved.hasOwnProperty(commentID)) {
                        this._getCommentContainer(commentID).html(
                            this._saved[commentID]);
                        this._onFirstLoad(commentID);
                        delete this._saved[commentID];
                    } else {
                        pendingCommentIDs.push(commentID);
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
                    const url = urlPrefix + pendingCommentIDs.join(',') +
                                urlSuffix;

                    this._addScript(url, () => {
                        _.each(pendingCommentIDs, this._onFirstLoad, this);
                    });
                } else {
                    /*
                     * We processed all we need to process above. Go to the
                     * next queue.
                     */
                    $.funcQueue(queueName).next();
                }
            });
        });

        // Clear the list.
        this._queue = {};

        $.funcQueue(queueName).start();
    },

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
    _getCommentContainer(commentID) {
        return $(`#${this.options.containerPrefix}_${commentID}`);
    },

    /*
     * When the expand button is clicked, trigger loading of a new diff
     * fragment with context.
     */
    _onExpandButtonClicked: function(e) {
        e.preventDefault();
        this._expandOrCollapse($(e.target).closest('.diff-expand-btn'), e);
    },

    /*
     * When the collapse button is clicked, trigger loading of a new diff
     * fragment with context.
     */
    _onCollapseButtonClicked: function(e) {
        e.preventDefault();
        this._expandOrCollapse($(e.target).closest('.diff-collapse-btn'), e);
    },

    /*
     * Update the positions of the collapse buttons.
     *
     * This will attempt to position the collapse buttons such that they're
     * in the center of the exposed part of the expanded diff fragment in the
     * current viewport.
     *
     * As the user scrolls, they'll be able to see the button scroll along
     * with them. It will not, however, leave the confines of the table.
     */
    _updateCollapseButtonPos: function() {
        this._centered.updatePosition();
    },

    /*
     * Add the given context above and below to the fragment corresponding to
     * the comment id.
     */
    _expandOrCollapse: function($btn) {
        var id = $btn.data('comment-id'),
            linesOfContext = $btn.data('lines-of-context'),
            url = this.options.reviewRequestPath + 'fragments/diff-comments/' +
                  id + '/?container_prefix=' + this.options.containerPrefix +
                  '&lines_of_context=' + linesOfContext + '&' + AJAX_SERIAL;

        this._addScript(url, this._onExpandOrCollapseFinished, id);

        RB.setActivityIndicator(true, {'type': 'GET'});
    },

    /**
     * Show the controls on the specified comment container.
     *
     * Args:
     *     diffEls (object):
     *         An object containing useful elements related to the diff
     *         fragment.
     */
    _showControls(diffEls) {
        /*
         * This will effectively control the opacity of the controls.
         */
        diffEls.$table
            .removeClass('collapsed')
            .addClass('expanded');

        /*
         * Undo all the transforms, so that these animate to their normal
         * positions.
         */
        diffEls.$thead.css('transform', '');
        diffEls.$diffHeaders.css('transform', '');
    },

    /**
     * Hide the controls on the specified comment container.
     *
     * Args:
     *     diffEls (object):
     *         An object containing useful elements related to the diff
     *         fragment.
     */
    _hideControls(diffEls) {
        diffEls.$table
            .removeClass('expanded')
            .addClass('collapsed');

        const $firstDiffHeader = diffEls.$diffHeaders.eq(0);

        if ($firstDiffHeader.hasClass('diff-header-above')) {
            /*
             * If the first diff header is present, we'll need to transition
             * the header down to be flush against the collapsed header.
             */
            const translateY = $firstDiffHeader.height() -
                               this.COLLAPSED_HEADERS_HEIGHT;

            diffEls.$thead.css('transform', `translateY(${translateY}px)`);
        }

        /*
         * The diff headers won't have the same heights exactly. We need to
         * compute the proper scale for the correct size per-header.
         */
        _.each(diffEls.$diffHeaders, diffHeaderEl => {
            const $diffHeader = $(diffHeaderEl);
            const scale = this.COLLAPSED_HEADERS_HEIGHT / $diffHeader.height();

            $diffHeader.css('transform', `scaleY(${scale})`);
        });
    },

    /*
     * Adds a script tag for a diff fragment to the bottom of the page. An
     * optional callback is added to the load event of the script tag. It is
     * called with the specified optional params.
     */
    _addScript: function(url, callback, params) {
        var e = document.createElement('script');

        e.type = 'text/javascript';
        e.src = url;

        if (callback !== undefined) {
            e.addEventListener('load', function () {
                callback(params);
            });
        }

        document.body.appendChild(e);
    },

    /*
     * Handle a expand or collapse finishing (i.e., the associated script tag
     * finished loading).
     */
    _onExpandOrCollapseFinished: function(id) {
        const $expanded = this._getCommentContainer(id);

        this._centered.setElements(new Map(
            Array.prototype.map.call(
                this.$('.diff-collapse-btn'),
                el => [el, $(el).closest('table')])
        ));
        this._updateCollapseButtonPos();

        RB.setActivityIndicator(false, {});

        this._tryHideControlsDelayed($expanded);
    },

    /**
     * Set up state for a fragment when it's first loaded.
     *
     * When a comment container loads its contents for the first time, the
     * controls will be hidden and the hover-related events will be registered
     * to allow the fragment to be expanded/collapsed.
     *
     * Args:
     *     id (string):
     *         The ID of the comment used to build the container ID.
     */
    _onFirstLoad(id) {
        const $container = this._getCommentContainer(id);
        const $table = $container.children('table');
        const $diffHeaders = $table.find('.diff-header');

        const diffEls = {
            $container: $container,
            $table: $table,
            $thead: $table.children('thead'),
            $diffHeaders: $diffHeaders,
            $controls: $diffHeaders.find('td > div'),
        };

        this._hideControls(diffEls);

        /*
         * Once we've hidden the controls, we want to enable transitions for
         * hovering. We don't apply this before (or make it implicit) because
         * we don't want all the transitions to take place on page load, as
         * it's both visually weird and messes with the height calculation for
         * the collapsed areas.
         */
        _.defer(() => $container.addClass('allow-transitions'));

        $container
            .hover(_.partial(this._tryShowControlsDelayed, diffEls),
                   _.partial(this._tryHideControlsDelayed, diffEls))
            .data('diff-fragment-loaded', true);
    },

    /**
     * Attempt to hide the controls in the given container after a delay.
     *
     * Args:
     *     diffEls (object):
     *         An object containing useful elements related to the diff
     *         fragment.
     */
    _tryShowControlsDelayed(diffEls) {
        _.delay(() => {
            if (diffEls.$container.is(':hover')) {
                this._showControls(diffEls);
            }
        }, this._timeout);
    },

    /**
     * Attempt to hide the controls in the given container after a delay.
     *
     * Args:
     *     diffEls (object):
     *         An object containing useful elements related to the diff
     *         fragment.
     */
    _tryHideControlsDelayed(diffEls) {
        _.delay(() => {
            if (!diffEls.$container.is(':hover')) {
                this._hideControls(diffEls);
            }
        }, this._timeout);
    }
});
