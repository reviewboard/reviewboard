/**
 * A SplitButtonView is a split button with a drop down which, when hovered
 * over, will drop down (or up) a list of alternative options.
 *
 *  If the view is to be removed, the remove() method must be called as this
 *  view adds elements to the DOM that are not under its root element.
 *
 */
RB.SplitButtonView = Backbone.View.extend({
    tag: 'div',
    className: 'split-btn',

    events: {
        'click .primary-btn': '_onClick',
        'mouseenter .drop-down-btn': '_showDropDown',
        'mouseleave': '_delayCheckHover',
    },

    /*
     * Note that whitespace really matters here. We don't want any spaces or
     * newlines between tags. This is why the indentation is missing and why
     * we're not using dedent``.
     */
    template: _.template([
        '<div class="btn btn-segmented">',
        '<div class="btn-segment primary-btn"><%- buttonText %></div>',
        '<div class="btn-segment drop-down-btn">',
        '<span class="rb-icon rb-icon-dropdown-arrow"></span>',
        '</div>',
        '</div>',
    ].join('')),

    /**
     * The delay time for animations in milliseconds.
     *
     * This must be the same value as ``@split-btn-hover-transition-time``
     * in css/defs.less.
     */
    _delayTime: 250,

    /**
     * Set up all initial state and event listeners.
     *
     * Args:
     *     options (object):
     *         Options for view construction.
     *
     * Option Args:
     *     text (string):
     *         The primary button text.
     *
     *     click (function or string):
     *         The handler for click events on the primary button.
     *
     *     id (string):
     *         The DOM ID to use for the primary button.
     *
     *     direction (string):
     *         The direction the drop-down will show; either ``up`` or
     *         ``down``.
     *
     *     alternatives (Array of object):
     *         A list of alternative buttons. Each item includes ``text``,
     *         ``click``, and ``id`` keys which are equivalent to the options
     *         for the primary button.
     */
    initialize(options={}) {
        this._dropDownShown = false;
        this._animating = false;

        this.options = options;
        this.options.alternatives = this.options.alternatives || [];

        if (this.options.direction === 'up') {
            this._dropDownShownClass = 'drop-up-shown';
        } else {
            this.options.direction = 'down';
            this._dropDownShownClass = 'drop-down-shown';
        }

        $(window).on('resize', this._onResize.bind(this));
    },

    /**
     * Remove the SplitButtonView from the DOM.
     */
    remove() {
        $(window).off('resize', this._onResize);
        this.stopListening();

        if (this._$alternatives) {
            this._$alternatives.remove();
        }

        if (this.$el) {
            this.$el.remove();
        }
    },

    /**
     * Render the split button.
     *
     * Returns:
     *     RB.SplitButtonView:
     *     This object, for chaining.
     */
    render() {
        this.$el
            .empty()
            .addClass(this.className)
            .html(this.template({
                buttonText: this.options.text
            }));

        const $segments = this.$el.children('.btn-segmented');
        this._$primaryBtn = $segments.children('.primary-btn');

        if (this.options.id) {
            this._$primaryBtn.attr('id', this.options.id);
        }

        this._$dropDownBtn = $segments.children('.drop-down-btn');
        this._$alternatives = $('<div class="split-btn-alternatives" />')
            .appendTo(this.$el)
            .hide();

        this.options.alternatives.forEach(alt => {
            const $btn = $('<div class="btn" />')
                .text(alt.text)
                .on('click', alt.click)
                .appendTo(this._$alternatives);

            if (alt.id) {
                $btn.attr('id', alt.id);
            }
        });

        return this;
    },

    /**
     * Handle the primary button being clicked.
     */
    _onClick() {
        this.options.click();
    },

    /**
     * Show the alternatives in a drop down (or up) menu.
     */
    _showDropDown() {
        if (this._dropDownShown || this._animating) {
            return;
        }

        this._animating = true;
        this._reposition();

        this._$alternatives.show();

        /*
         * Wait for the menu to be shown so we can start applying the
         * opacity transition.
         */
        _.defer(() => {
            this.$el.addClass(this._dropDownShownClass);
            this._$dropDownBtn.addClass('hover');

            setTimeout(() => {
                this._dropDownShown = true;
                this._animating = false;
            }, this._delayTime);
        });
    },

    /**
     * Try to hide the drop down menu.
     *
     * The menu will only be hidden if it's shown and not currently animating.
     */
    _tryHideDropDown() {
        if (!this._dropDownShown || this._animating || this.$el.is(':hover')) {
            return;
        }

        this._animating = true;

        this._$dropDownBtn.removeClass('hover');
        this.$el.removeClass(this._dropDownShownClass);

        setTimeout(() => {
            this._dropDownShown = false;
            this._animating = false;
            this._$alternatives
                .hide()
                .css({
                    top: null,
                    bottom: null,
                });
        }, this._delayTime);
    },

    /**
     * Schedule a hover check to try to hide the drop down when the mouse
     * leaves.
     */
    _delayCheckHover() {
        _.delay(this._tryHideDropDown.bind(this), this._delayTime);
    },

    /**
     * Position the drop-down menu above or below the button.
     */
    _reposition() {
       this._$alternatives.css(
           this.options.direction === 'down' ? 'top' : 'bottom',
           this._$primaryBtn.outerHeight());
    },

    /**
     * Handle a screen resize event to reposition the drop-down.
     */
    _onResize: _.debounce(function() {
        if (this._dropDownShown) {
            this._reposition();
        }
    }, 300)
});
