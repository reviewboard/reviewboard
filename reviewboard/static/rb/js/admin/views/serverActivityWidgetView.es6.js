/**
 * Displays a graph of the activity on the server.
 */
RB.Admin.ServerActivityWidgetView = RB.Admin.WidgetView.extend({
    /**
     * Render the widget.
     */
    renderWidget() {
        let previousHoverPoint = null;

        this._$tooltip = $();
        this._$chart = $('<div class="rb-c-admin-server-activity-widget__chart">')
            .appendTo(this.$content)
            .bind('plothover', (ev, pos, item) => {
                if (item) {
                    if (previousHoverPoint !== item.dataIndex) {
                        const x = new Date(item.datapoint[0]).toLocaleDateString();
                        const y = item.datapoint[1];

                        previousHoverPoint = item.dataIndex;

                        this._$tooltip = $('<div class="rb-c-admin-server-activity-widget-tooltip">')
                            .text(`${item.series.label} on ${x}: ${y}`)
                            .appendTo('body')
                            .css({
                                left: `${item.pageX + 5}px`,
                                top: `${item.pageY + 5}px`,
                            })
                            .fadeIn(200);
                    }
                } else {
                    this._$tooltip.remove();
                    this._$tooltip = $();
                    previousHoverPoint = null;
                }
            });

        this._addClickAction({
            id: 'prev',
            text: '<',
            loadKey: 'prev',
        });

        this._addClickAction({
            id: 'next',
            text: '>',
            loadKey: 'next',
        });

        this._addToggleAction({
            id: 'show-reviews',
            text: _('Reviews'),
            toggleKey: 'reviews',
        });

        this._addToggleAction({
            id: 'show-comments',
            text: _('Comments'),
            toggleKey: 'comments',
        });


        this._addToggleAction({
            id: 'show-review-requests',
            text: _('Review Requests'),
            toggleKey: 'reviewRequests',
        });

        this._addToggleAction({
            id: 'show-changes',
            text: _('Changes'),
            toggleKey: 'changeDescriptions',
        });

        this._addToggleAction({
            id: 'show-legend',
            text: _('Legend'),
            toggleKey: 'legend',
        });

        this.listenTo(this.model, 'updated', this._update);

        this.model.loadData('none');
    },


    /**
     * Add a click action to the footer.
     *
     * Args:
     *     options (object):
     *         Options for the action.
     *
     * Option Args:
     *     id (string):
     *         The ID for the action.
     *
     *     text (string):
     *         The text to display.
     *
     *     loadKey (string):
     *         The key to use when loading new data from the server.
     */
    _addClickAction(options) {
        const $action = this.addFooterAction({
            id: options.id,
            html: `<a href="#">${options.text}</a>`,
        });

        $action.click(ev => {
            ev.preventDefault();
            ev.stopPropagation();

            this.model.loadData(options.loadKey);
        });
    },

    /**
     * Add a toggle action to the footer.
     *
     * Args:
     *     options (object):
     *         Options for the action.
     *
     * Option Args:
     *     id (string):
     *         The ID for the action.
     *
     *     text (string):
     *         The text to display.
     *
     *     toggleKey (string):
     *         The key to toggle in the ``show`` settings for the model.
     */
    _addToggleAction(options) {
        const $action = this.addFooterAction({
            id: options.id,
            html: `<a href="#">${options.text}</a>`,
        });

        $action.click(ev => {
            ev.preventDefault();
            ev.stopPropagation();

            const show = this.model.get('show');
            show[options.toggleKey] = !show[options.toggleKey];
            this.model.set('show', show);
            this.model.loadData('same');
        });
    },

    /**
     * Update the displayed graph.
     */
    _update() {
        const options = {
            xaxis: {
                mode: 'time',
                tickLength: 1,
                min: moment(this.model.get('rangeStart')).valueOf(),
                max: moment(this.model.get('rangeEnd')).valueOf(),
            },
            yaxis: {
                min: 0,
                tickDecimals: 0,
            },
            grid: {
                markings: axes => {
                    // This will shade weekends.
                    const markings = [];
                    const d = new Date(axes.xaxis.min);

                    // Go to the first Saturday.
                    d.setUTCDate(d.getUTCDate() - ((d.getUTCDay() + 1) % 7));
                    d.setUTCSeconds(0);
                    d.setUTCMinutes(0);
                    d.setUTCHours(0);

                    let i = d.getTime();

                    do {
                        /*
                         * When we don't set yaxis, the rectangle automatically
                         * extends to infinity upwards and downwards.
                         */
                        markings.push({
                            xaxis: {from: i, to: i + 2 * 24 * 60 * 60 * 1000},
                        });
                        i += 7 * 24 * 60 * 60 * 1000;
                    } while (i < axes.xaxis.max);

                    return markings;
                },
                hoverable: true,
            },
            series: {
                points: {
                    show: true,
                    radius: 3,
                },
                lines: {
                    show: true,
                },
            },
            legend: {
                position: 'nw',
                show: this.model.get('show').legend,
            },
        };

        const datasets = [];

        if (this.model.get('show').changeDescriptions) {
            datasets.push({
                label: _('Change Descriptions'),
                data: this.model.get('data').changeDescriptions,
                bars: { show: true, },
                lines: { show: false, },
                color: 0,
            });
        }

        if (this.model.get('show').comments) {
            datasets.push({
                label: _('Comments'),
                data: this.model.get('data').comments,
                bars: { show: true, },
                lines: { show: false, },
                color: 1,
            });
        }

        if (this.model.get('show').reviewRequests) {
            datasets.push({
                label: _('Review Requests'),
                data: this.model.get('data').reviewRequests,
                bars: { show: true, },
                lines: { show: false, },
                color: 2,
            });
        }

        if (this.model.get('show').reviews) {
            datasets.push({
                label: _('Reviews'),
                data: this.model.get('data').reviews,
                bars: { show: true, },
                lines: { show: false, },
                color: 3,
            });
        }

        if (datasets.length === 0) {
            datasets.push({
                bars: { show: true, },
                lines: { show: false, },
            });
        }

        $.plot(this._$chart, datasets, options);
    },
});
