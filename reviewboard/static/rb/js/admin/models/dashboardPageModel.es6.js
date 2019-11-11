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
});
