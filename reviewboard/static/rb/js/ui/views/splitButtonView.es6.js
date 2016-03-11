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
        'mouseleave .drop-down-btn': '_delayCheckHover'
    },

    template: _.template([
        '<div class="btn primary-btn"><%- buttonText %></div>',
        '<div class="btn drop-down-btn">&#9662;</div>'
    ].join('')),

    /**
     * The delay time for animations.
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
     *     zIndex (number):
     *         The optional z-index for the drop-down menu.
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

        _.bindAll(this, '_tryHideDropDown', '_onResize', '_delayCheckHover');

        $(window).on('resize', this._onResize);
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

        this._$primaryBtn = this.$('.primary-btn');

        if (this.options.id) {
            this._$primaryBtn.attr('id', this.options.id);
        }

        this._$dropDownBtn = this.$('.drop-down-btn');
        this._$alternatives = $('<div class="split-btn-alternatives" />')
            .appendTo(document.body)
            .hide();

        if (this.options.zIndex) {
            this._$alternatives.css('zIndex', this.options.zIndex);
        }

        for (let alt of this.options.alternatives) {
            const $btn = $('<div class="btn" />')
                .text(alt.text)
                .on('click', alt.click)
                .appendTo(this._$alternatives);

            if (alt.id) {
                $btn.attr('id', alt.id);
            }
        }

        const width = Math.max(this._$alternatives.width(), this.$el.width());

        this._$alternatives.width(width);
        this._$primaryBtn.width(
            width - this._$primaryBtn.getExtents('b', 'r') -
            this._$dropDownBtn.outerWidth() -
            this._$dropDownBtn.getExtents('mbp', 'lr'));

        this._$alternatives
            .width(width)
            .on('mouseleave', this._delayCheckHover);

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

        if (!this._dropDownShown && !this._animating) {
            this._$primaryBtn.addClass(this._dropDownShownClass);
            this._$dropDownBtn.addClass(this._dropDownShownClass + ' hover');
            this._$alternatives.addClass(this._dropDownShownClass);
            this._animating = true;
            this._reposition();

            this._$alternatives
                .fadeIn(this._delayTime, () => {
                    this._dropDownShown = true;
                    this._animating = false;
                });

        }
    },

    /**
     * Try to hide the drop down menu.
     *
     * The menu will only be hidden if it is shown and
     */
    _tryHideDropDown() {
        if (this._dropDownShown &&
            !this._animating &&
            !this._$dropDownBtn.is(':hover') &&
            !this._$alternatives.is(':hover')) {
            this._$dropDownBtn
                .removeClass(this._dropDownShownClass + ' hover');
            this._$primaryBtn.removeClass(this._dropDownShownClass);
            this._animating = true;

            this._$alternatives.fadeOut(this._delayTime, () => {
                this._dropDownShown = false;
                this._animating = false;
                this._$alternatives.removeClass(this._dropDownShownClass);
            });
        }
    },

    /**
     * Schedule a hover check to try to hide the drop down when the mouse
     * leaves.
     */
    _delayCheckHover() {
        _.delay(this._tryHideDropDown, this._delayTime);
    },

    /**
     * Position the drop-down menu above or below the button.
     */
    _reposition() {
        this._$alternatives.positionToSide(this.$el, {
            side: this.options.direction === 'down' ? 'b' : 't'
        });
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
