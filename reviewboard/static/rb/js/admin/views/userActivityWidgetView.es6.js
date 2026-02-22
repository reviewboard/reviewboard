/**
 * Displays stats on how often users have logged in or used Review Board.
 *
 * This is displayed as a pie graph, with a legend alongside it breaking
 * down the activity into 1-6 day, 7-29 day, 30-59 day, 60-89 day, and 90+
 * day ranges.
 */
RB.Admin.UserActivityWidgetView = RB.Admin.WidgetView.extend({
    template: _.template(dedent`
        <div class="rb-c-admin-user-activity-widget__chart"></div>
        <div class="rb-c-admin-user-activity-widget__user-total">
         <%- userTotalLabel %>: <strong><%- totalUsers %></strong>
        </div>
    `),

    /**
     * Render the widget.
     *
     * This will build the basic structure of the widget's content and
     * then plot the chart.
     */
    renderWidget() {
        this.$content.html(this.template({
            totalUsers: this.model.get('total'),
            userTotalLabel: gettext('Total Users'),
        }));

        this._$chart = this.$('.rb-c-admin-user-activity-widget__chart');

        this._plotData();
    },

    /**
     * Handle updates to the size of the widget.
     *
     * This will re-render the chart for the new size.
     */
    updateSize() {
        this._plotData();
    },

    /**
     * Plot user activity into a chart.
     */
    _plotData() {
        const model = this.model;
        const now = model.get('now');
        const sevenDays = model.get('sevenDays');
        const thirtyDays = model.get('thirtyDays');
        const sixtyDays = model.get('sixtyDays');
        const ninetyDays = model.get('ninetyDays');

        $.plot(
            this._$chart,
            [
                {
                    data: now,
                    label: interpolate(gettext('Active (%s)'),
                                       [now]),
                },
                {
                    data: sevenDays,
                    label: interpolate(gettext('7 days ago (%s)'),
                                       [sevenDays]),
                },
                {
                    data: thirtyDays,
                    label: interpolate(gettext('30 days ago (%s)'),
                                       [thirtyDays]),
                },
                {
                    data: sixtyDays,
                    label: interpolate(gettext('60 days ago (%s)'),
                                       [sixtyDays]),
                },
                {
                    data: ninetyDays,
                    label: interpolate(gettext('90 days ago (%s)'),
                                       [ninetyDays]),
                },
            ],
            {
                series: {
                    pie: {
                        show: true,
                        label: {
                            show: true,
                            radius: 1,
                            background: {
                                opacity: 0.8,
                            },
                            formatter: (label, series) =>
                                `<div>${Math.round(series.percent)}%</div>`,
                        },
                    },
                },
            }
        );

        this.trigger('sizeChanged');
    },
});
