/**
 * The UI for an administration dashboard widget.
 *
 * This can be subclassed by widgets in order to add custom widget actions and
 * content. Subclasses can render the widget by overriding
 * :js:func:`RB.Admin.WidgetView.renderWidget()`, and respond to layout and
 * size changes by overriding :js:func:`RB.Admin.WidgetView.updateSize()`.
 */
RB.Admin.WidgetView = Backbone.View.extend({
    /**
     * Initialize the widget.
     */
    initialize() {
        this.$header = null;
        this.$content = null;
        this.$footer = null;
        this.$headerActions = null;
        this.$footerActions = null;
    },

    /**
     * Render the widget.
     *
     * Returns:
     *     RB.Admin.WidgetView:
     *     This widget, for chaining purposes.
     */
    render() {
        this.$header = this.$el.children('.rbc-admin-widget__header');
        this.$content = this.$el.children('.rb-c-admin-widget__content');
        this.$footer = this.$el.children('.rb-c-admin-widget__footer');
        this.$headerActions = this.$header.children(
            '.rb-c-admin-widget__actions');
        this.$footerActions = this.$footer.children(
            '.rb-c-admin-widget__actions');

        this.renderWidget();

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
});
