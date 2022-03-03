/**
 * State and operations for the server activity graph admin widget.
 *
 * Model Attributes:
 *     data (dict):
 *         A dictionary containing the data to display for the graph.
 *
 *     rangeStart (string):
 *         The beginning of the date range shown, in YYYY-MM-DD format.
 *
 *     rangeEnd (string):
 *         The end of the date range shown, in YYYY-MM-DD format.
 */
RB.Admin.ServerActivityWidget = RB.Admin.Widget.extend({
    defaults: _.defaults({
        data: {
            changeDescriptions: [],
            comments: [],
            reviewRequests: [],
            reviews: [],
        },
        rangeStart: '',
        rangeEnd: '',
        show: {
            changeDescriptions: true,
            comments: true,
            legend: true,
            reviewRequests: true,
            reviews: true,
        },
    }, RB.Admin.Widget.prototype.defaults),

    /**
     * Reload data from the server.
     *
     * Args:
     *     direction (string):
     *         A direction to move from the currently-shown period.
     */
    loadData(direction) {
        fetch(`widget-activity/?range_start=${this.attributes.rangeStart}&range_end=${this.attributes.rangeEnd}&direction=${direction}`)
            .then(rsp => rsp.json())
            .then(rsp => {
                this.set({
                    rangeStart: rsp.range.range_start,
                    rangeEnd: rsp.range.range_end,
                    data: {
                        changeDescriptions: rsp.activity_data.change_descriptions,
                        comments: rsp.activity_data.comments,
                        reviewRequests: rsp.activity_data.review_requests,
                        reviews: rsp.activity_data.reviews,
                    }
                });

                this.trigger('updated');
            });
    },
});
