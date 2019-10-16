/**
 * State for the administration UI's main dashboard page.
 *
 * Model Attributes:
 *     supportData (string):
 *         An encoded payload containing information used to look up
 *         information on an active support contract for the server.
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
        });
    },
});
