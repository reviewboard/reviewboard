/**
 * A view for managing a loaded diff fragment and its state.
 *
 * This displays a fragment of a diff, offering options for expanding and
 * collapsing content.
 */
RB.DiffFragmentView = Backbone.View.extend({
    events: {
        'click .diff-expand-btn': '_onExpandButtonClicked',
        'click .diff-collapse-btn': '_onCollapseButtonClicked',
        'mouseenter': '_tryShowControlsDelayed',
        'mouseleave': '_tryHideControlsDelayed',
    },

    /** The exposed headers height to show when collapsed. */
    COLLAPSED_HEADERS_HEIGHT: 4,

    /** The timeout for a mouseout event to fire after it actually occurs. */
    _controlsHoverTimeout: 250,

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object, optional):
     *         Options that control the view. This must at least provide
     *         ``loadDiff``.
     *
     * Option Args:
     *     collapsible (bool, optional):
     *         Whether or not the controls on the view can be collapsed. If
     *         collapsible, they will also start collapsed. This defaults to
     *         ``false``.
     *
     *     loadDiff (function):
     *         The function to call to load more of the diff. This must be
     *         provided by the caller.
     */
    initialize(options={}) {
        this._loadDiff = options.loadDiff;
        this._collapsible = !!options.collapsible;

        this._$table = null;
        this._$thead = null;
        this._$diffHeaders = null;
        this._$controls = null;

        this._centeredMgr = null;
        this._contextExpanded = false;
    },

    /**
     * Render the view.
     *
     * This will start the view off in a collapsed mode.
     *
     * Returns:
     *     RB.DiffFragmentView:
     *     This instance, for chaining.
     */
    render() {
        /*
         * Make sure this class isn't on the fragment, in case we're
         * reloading content.
         */
        this.$el.removeClass('allow-transitions');

        this._$table = this.$el.children('table');
        this._$diffHeaders = this._$table.find('.diff-header');
        this._$thead = this._$table.children('thead');
        this._$controls = this._$diffHeaders.find('td > div');

        if (this._collapsible && this.$el.is(':visible')) {
            this.hideControls();
        } else {
            /*
             * If we're not collapsible, then we're always expanded
             * by default.
             */
            this.showControls();
        }

        if (this._collapsible) {
            /*
             * Once we've hidden the controls, we want to enable transitions for
             * hovering. We don't apply this before (or make it implicit)
             * because we don't want all the transitions to take place on page
             * load, as it's both visually weird and messes with the height
             * calculation for the collapsed areas.
             */
            _.defer(() => this.$el.addClass('allow-transitions'));
        }

        return this;
    },

    /**
     * Show the controls on the specified comment container.
     */
    showControls() {
        /* This will effectively control the opacity of the controls. */
        this._$table
            .removeClass('collapsed')
            .addClass('expanded');

        /*
         * Undo all the transforms, so that these animate to their normal
         * positions.
         */
        this._$thead.css('transform', '');
        this._$diffHeaders.css('transform', '');
    },

    /**
     * Hide the controls on the specified comment container.
     *
     * Args:
     *     animate (boolean, optional):
     *         Whether to animate hiding the controls. By default, this is
     *         ``true``.
     */
    hideControls(animate) {
        /*
         * Never hide the controls when context has been expanded. It creates
         * a sort of jarring initial effect.
         */
        if (this._contextExpanded) {
            return;
        }

        if (animate === false) {
            this.$el.removeClass('allow-transitions');
        }

        this._$table
            .removeClass('expanded')
            .addClass('collapsed');

        const $firstDiffHeader = this._$diffHeaders.eq(0);

        if ($firstDiffHeader.hasClass('diff-header-above')) {
            /*
             * If the first diff header is present, we'll need to transition
             * the header down to be flush against the collapsed header.
             */
            const translateY = $firstDiffHeader.height() -
                               this.COLLAPSED_HEADERS_HEIGHT;

            this._$thead.css('transform', `translateY(${translateY}px)`);
        }

        /*
         * The diff headers won't have the same heights exactly. We need to
         * compute the proper scale for the correct size per-header.
         */
        _.each(this._$diffHeaders, diffHeaderEl => {
            const $diffHeader = $(diffHeaderEl);
            const scale = this.COLLAPSED_HEADERS_HEIGHT / $diffHeader.height();

            $diffHeader.css('transform', `scaleY(${scale})`);
        });

        if (animate === false) {
            _.defer(() => this.$el.addClass('allow-transitions'));
        }
    },

    /*
     * Common functionality around expand or collapsing the diff fragment.
     *
     * This will grab information from the expand/collapse button provided
     * and load a new diff fragment representing the state described in that
     * button. The new diff will represent either an expanded or collapsed
     * state.
     *
     * Args:
     *     $btn (jQuery):
     *         The button element that triggered the event leading to this
     *         function call.
     */
    _expandOrCollapse($btn) {
        this._loadDiff({
            linesOfContext: $btn.data('lines-of-context'),
            onDone: this._onExpandOrCollapseFinished.bind(this),
        });
    },

    /**
     * Attempt to hide the controls in the given container after a delay.
     */
    _tryShowControlsDelayed() {
        if (this._collapsible) {
            _.delay(() => {
                if (this.$el.is(':hover')) {
                    this.showControls();
                }
            }, this._controlsHoverTimeout);
        }
    },

    /**
     * Attempt to hide the controls in the given container after a delay.
     */
    _tryHideControlsDelayed() {
        if (this._collapsible) {
            _.delay(() => {
                if (!this.$el.is(':hover')) {
                    this.hideControls();
                }
            }, this._controlsHoverTimeout);
        }
    },

    /*
     * Handler for when an expanded or collapsed fragment has loaded.
     *
     * This will reset the state of the view, based on the new fragment, and
     * re-render the view.
     */
    _onExpandOrCollapseFinished() {
        RB.setActivityIndicator(false, {});

        /* All our HTML has changed, so clean up and re-render everything. */
        if (this._centeredMgr !== null) {
            this._centeredMgr.remove();
            this._centeredMgr = null;
        }

        const $collapseButtons = this.$('.diff-collapse-btn');

        /*
         * Check if we have any collapse buttons. If so, we'll need to track
         * them in a CenteredElementManager.
         */
        if ($collapseButtons.length > 0) {
            this._centeredMgr = new RB.CenteredElementManager({
                elements: new Map(Array.prototype.map.call(
                    $collapseButtons,
                    el => {
                        const $chunks = $(el)
                            .closest('.sidebyside')
                            .children('tbody')
                            .not('.diff-header');

                        return [el, {
                            $top: $chunks.eq(0),
                            $bottom: $chunks.eq(-1),
                        }];
                    }))
            });
            this._centeredMgr.updatePosition();

            this._contextExpanded = true;
        } else {
            this._contextExpanded = false;
        }

        this.render();

        if (!this._contextExpanded) {
            this._tryHideControlsDelayed();
        }
    },

    /**
     * Expand a diff fragment.
     *
     * When the expand button is clicked, this will trigger loading of a
     * new diff fragment containing the context as defined by the data
     * attributes on the button.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    _onExpandButtonClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._expandOrCollapse($(e.target).closest('.diff-expand-btn'), e);
    },

    /**
     * Collapse an expanded diff fragment.
     *
     * When the collapse button is clicked, this will trigger loading of a
     * new diff fragment containing the context as defined by the data
     * attributes on the button.
     *
     * Args:
     *     e (Event):
     *         The click event.
     */
    _onCollapseButtonClicked(e) {
        e.preventDefault();
        e.stopPropagation();

        this._expandOrCollapse($(e.target).closest('.diff-collapse-btn'), e);
    },
});
