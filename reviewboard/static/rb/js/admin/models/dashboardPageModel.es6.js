/**
 * State for the administration UI's main dashboard page.
 *
 * Model Attributes:
 *     supportData (string):
 *         An encoded payload containing information used to look up
 *         information on an active support contract for the server.
 *
 *     widgetsData (Array of object):
 *         Metadata on all the widgets rendered on the page. Each entry in
 *         the array is an object containing:
 *
 *         ``id``:
 *             The ID of the widget.
 *
 *         ``domID``:
 *             The DOM element ID of the widget's rendered HTML.
 *
 *         ``modelClass``:
 *             The namespaced name of the model class managing the widget's
 *             state.
 *
 *         ``modelAttrs``:
 *             The optional attributes passed to the widget model during
 *             initialization.
 *
 *         ``modelOptions``:
 *             The optional options passed to the widget model during
 *             initialization.
 *
 *         ``viewClass``:
 *             The namespaced name of the view class rendering the widget.
 *
 *         ``viewOptions``:
 *             The optional options passed to the widget view during
 *             initialization.
 */
RB.Admin.DashboardPage = RB.Page.extend({
    /**
     * Return the default attribute values.
     *
     * Returns:
     *     object:
     *     The default attribute values.
     */
    defaults() {
        return _.defaults(_.result(RB.Page.prototype.defaults), {
            supportData: null,
            widgetsData: [],
        });
    },

    /**
     * Initialize the page.
     */
    initialize() {
        RB.Page.prototype.initialize.apply(this, arguments);

        this.widgets = new Backbone.Collection();
    },

    /**
     * Load the widgets from the serialized widget data.
     *
     * This will construct a model for each widget, and call the provided
     * function to finish any UI-side setup.
     *
     * If any widgets fail to load, they'll be skipped.
     *
     * Args:
     *     onWidgetLoaded (function):
     *         The function to call for each widget. This takes the widget
     *         model and serialized widget information as parameters.
     */
    loadWidgets(onWidgetLoaded) {
        const classTypes = {};
        const widgetsData = this.get('widgetsData');

        this.widgets.reset();

        for (let i = 0; i < widgetsData.length; i++) {
            const widgetInfo = widgetsData[i];

            try {
                let ModelType = classTypes[widgetInfo.modelClass];
                let ViewType = classTypes[widgetInfo.viewClass];

                if (ModelType === undefined) {
                    ModelType = Djblets.getObjectByName(widgetInfo.modelClass);
                    classTypes[widgetInfo.modelClass] = ModelType;
                }

                if (ViewType === undefined) {
                    ViewType = Djblets.getObjectByName(widgetInfo.viewClass);
                    classTypes[widgetInfo.viewClass] = ViewType;
                }

                const widgetModel = new ModelType(
                    _.defaults(
                        {
                            id: widgetInfo.id,
                        },
                        widgetInfo.modelAttrs),
                    widgetInfo.modelOptions);

                this.widgets.add(widgetModel);

                onWidgetLoaded({
                    domID: widgetInfo.domID,
                    ViewType: ViewType,
                    viewOptions: widgetInfo.viewOptions,
                    widgetModel: widgetModel,
                });
            } catch (e) {
                console.error(
                    'Unable to render administration widget "%s": %s',
                    widgetInfo.id, e);
            }
        }
    },
});
