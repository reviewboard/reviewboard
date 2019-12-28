/**
 * The UI for an administration dashboard widget.
 *
 * This can be subclassed by widgets in order to add custom widget actions and
 * content. Subclasses can render the widget by overriding
 * :js:func:`RB.Admin.WidgetView.renderWidget()`, and respond to layout and
 * size changes by overriding :js:func:`RB.Admin.WidgetView.updateSize()`.
 */
RB.Admin.WidgetView = Backbone.View.extend({
    events: {
        'click .js-action-reload': 'reloadContent',
    },

    /** Whether this widget can reload its contents on request. */
    canReload: false,

    /** Whether this widget can reload its contents on request. */
    reloadTitle: null,

    /**
     * Initialize the widget.
     */
    initialize() {
        this.$header = null;
        this.$content = null;
        this.$footer = null;
        this.$headerActions = null;
        this.$footerActions = null;
        this._$reloadAction = null;
    },

    /**
     * Add an action to the header.
     *
     * Args:
     *     options (object):
     *         Options for the action.
     *
     * Option Args:
     *     id (string):
     *         The ID of the action. This will be used to add a CSS class
     *         in the form of :samp:`js-action-{id}`.
     *
     *     cssClasses (string, optional):
     *         A space-separated list of CSS class names to add to the
     *         action.
     *
     *     el (Element or jQuery, optional):
     *         An optional element to add to the action. This takes
     *         precedence over ``html`` and ``text``.
     *
     *     html (string, optional):
     *         Optional HTML to insert into the action. This takes
     *         precedence over ``text``.
     *
     *     text (string, optional):
     *         Optional plain text to set inside the action.
     *
     *     title (string, optional):
     *         Optional title to display when hovering over the action,
     *         or for screen readers.
     *
     * Returns:
     *     jQuery:
     *     The resulting action element.
     */
    addHeaderAction(options) {
        return this._buildAction(options)
            .appendTo(this.$headerActions);
    },

    /**
     * Add an action to the footer.
     *
     * Args:
     *     options (object):
     *         Options for the action.
     *
     * Option Args:
     *     id (string):
     *         The ID of the action. This will be used to add a CSS class
     *         in the form of :samp:`js-action-{id}`.
     *
     *     cssClasses (string, optional):
     *         A space-separated list of CSS class names to add to the
     *         action.
     *
     *     el (Element or jQuery, optional):
     *         An optional element to add to the action. This takes
     *         precedence over ``html`` and ``text``.
     *
     *     html (string, optional):
     *         Optional HTML to insert into the action. This takes
     *         precedence over ``text``.
     *
     *     text (string, optional):
     *         Optional plain text to set inside the action.
     *
     *     title (string, optional):
     *         Optional title to display when hovering over the action,
     *         or for screen readers.
     *
     * Returns:
     *     jQuery:
     *     The resulting action element.
     */
    addFooterAction(options) {
        return this._buildAction(options)
            .appendTo(this.$footerActions);
    },

    /**
     * Show to the user whether or not content is loading/reloading.
     *
     * This will set whether the reloading action icon is spinning.
     *
     * Args:
     *     reloading (boolean):
     *         Whether to show to the user that content is reloading.
     */
    setReloading(reloading) {
        console.assert(this.canReload,
                       'This widget did not set canReload=true.');

        this._$reloadAction.toggleClass('fa-spin', reloading);
    },

    /**
     * Render the widget.
     *
     * Returns:
     *     RB.Admin.WidgetView:
     *     This widget, for chaining purposes.
     */
    render() {
        this.$header = this.$el.children('.rb-c-admin-widget__header');
        this.$content = this.$el.children('.rb-c-admin-widget__content');
        this.$footer = this.$el.children('.rb-c-admin-widget__footer');
        this.$headerActions = this.$header.children(
            '.rb-c-admin-widget__actions');
        this.$footerActions = this.$footer.children(
            '.rb-c-admin-widget__actions');

        if (this.canReload) {
            this._$reloadAction = this.addHeaderAction({
                id: 'reload',
                cssClasses: 'fa fa-refresh',
                title: this.reloadTitle,
            });
        }

        this.renderWidget();

        /* This is needed only for legacy widgets. */
        this.$el.trigger('widget-shown');

        return this;
    },

    /**
     * Render the content of the widget.
     *
     * This will only be called once, when the widget is first rendered. It
     * should take care of any initial content shown in the widget, and should
     * attach any event listeners needed to perform updates to the content.
     */
    renderWidget() {
    },

    /**
     * Update the rendered size of the widget.
     *
     * This may be called in response to changes in the widget size, such as
     * when manually resizing the page or switching between desktop and mobile
     * modes.
     *
     * This should perform any changes needed to the rendered size of any
     * non-responsive UI elements in the widget.
     */
    updateSize() {
    },

    /**
     * Reload the content inside the widget.
     *
     * This is called in response to a user clicking the Reload action,
     * if :js:attr:`RB.Admin.WidgetView.canReload` is set to ``true``.
     */
    reloadContent() {
    },

    /**
     * Build an action.
     *
     * Args:
     *     options (object):
     *         Options for the action.
     *
     * Option Args:
     *     id (string):
     *         The ID of the action. This will be used to add a CSS class
     *         in the form of :samp:`js-action-{id}`.
     *
     *     cssClasses (string, optional):
     *         A space-separated list of CSS class names to add to the
     *         action.
     *
     *     el (Element or jQuery, optional):
     *         An optional element to add to the action. This takes
     *         precedence over ``html`` and ``text``.
     *
     *     html (string, optional):
     *         Optional HTML to insert into the action. This takes
     *         precedence over ``text``.
     *
     *     text (string, optional):
     *         Optional plain text to set inside the action.
     *
     *     title (string, optional):
     *         Optional title to display when hovering over the action,
     *         or for screen readers.
     *
     * Returns:
     *     jQuery:
     *     The resulting action element.
     */
    _buildAction(options) {
        console.assert(options.id, 'An "id" value must be provided');

        const $action = $('<li class="rb-c-admin-widget__action">')
            .addClass(`js-action-${options.id}`);

        if (options.cssClasses) {
            $action.addClass(options.cssClasses);
        }

        if (options.el) {
            $action.append(options.el);
        } else if (options.html) {
            $action.html(options.html);
        } else if (options.text) {
            $action.text(options.text);
        }

        if (options.title) {
            $action.attr('title', options.title);
        }

        return $action;
    },
});
