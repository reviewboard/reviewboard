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
        this._centered = new RB.CenteredElementManager();

        _.bindAll(this, '_onExpandOrCollapseFinished',
                  '_updateCollapseButtonPos', '_tryHideControlsDelayed',
                  '_tryShowControlsDelayed');
    },

    /*
     * Remove this from the DOM and set all the elements it references to null
     */
    remove: function() {
        RB.AbstractReviewableView.prototype.remove.call(this);

        this._$window = null;
        this._active = null;
    },

    /*
     * Queues the load of a diff fragment from the server.
     *
     * This will be added to a list, which will fetch the comments in batches
     * based on file IDs.
     */
    queueLoad: function(comment_id, key) {
        var queue = this._queue;

        if (!queue[key]) {
            queue[key] = [];
        }

        queue[key].push(comment_id);
    },

    /*
     * Begins the loading of all diff fragments on the page belonging to
     * the specified queue.
     */
    loadFragments: function() {
        var queueName = this.options.queueName,
            urlPrefix,
            urlSuffix;

        if (!this._queue) {
            return;
        }

        urlPrefix = this.options.reviewRequestPath +
                    'fragments/diff-comments/';
        urlSuffix = '/?queue=' + queueName +
                    '&container_prefix=' + this.options.containerPrefix +
                    '&' + TEMPLATE_SERIAL;

        _.each(this._queue, function(comments) {
            var url = urlPrefix + comments.join(',') + urlSuffix;

            $.funcQueue(queueName).add(_.bind(function() {
                this._addScript(url,
                                _.bind(function() {
                                    _.each(comments, this._onFirstLoad, this);
                                }, this)
                );
            }, this));
        }, this);

        // Clear the list.
        this._queue = {};

        $.funcQueue(queueName).start();
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
        var $expanded = this.$('#' + this.options.containerPrefix + '_' + id);

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
        const $container = this.$(`#${this.options.containerPrefix}_${id}`);
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

        $container.hover(_.partial(this._tryShowControlsDelayed, diffEls),
                         _.partial(this._tryHideControlsDelayed, diffEls));
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
