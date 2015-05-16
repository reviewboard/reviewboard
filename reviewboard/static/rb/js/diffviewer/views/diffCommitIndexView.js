/*
 * The DiffCommitIndexView displays a table containing diff commit entries.
 *
 * The view contains all the commits associated with the diff revision selected
 * by the diff revision selector.
 */
RB.DiffCommitIndexView = Backbone.View.extend({
    /*
     * Initialize the view.
     */
    initialize: function() {
        this._$itemsTable = null;
        this._$body = $(document.body);

        this.collection = this.options.collection;
        this.listenTo(this.collection, 'update', this.update);

        _.bindAll(this, '_onExpandSummary');
    },

    _itemTemplate: _.template([
        '<tr class="commit-entry-<%- historyEntryType%>">',
        ' <% if (renderHistorySymbol) { %>',
        ' <td class="commit-entry-type"><%- historyEntrySymbol %></td>',
        ' <% } %>',
        ' <td class="diff-file-icon"></td>',
        ' <td class="diff-commit-summary data-diff-commit-cid="<%- cid %>">',
        '  <%- summary %>',
        '</td>',
        ' <td class="diff-commit-author"><%- authorName %></td>',
        '</tr>'
    ].join('')),

    _tableHeader: _.template([
        '<thead>',
        ' <tr>',
        '  <% if (renderHistorySymbol) { %>',
        '  <th></th>',
        '  <% } %>',
        '  <th></th>',
        '  <th><%- gettext("Summary") %></th>',
        '  <th><%- gettext("Author") %></th>',
        ' </tr>',
        '</thead>'
    ].join('')),

    /*
     * Render the diff commit list table.
     */
    render: function() {
        this._$itemsTable = $('<table/>').appendTo(this.$el);

        this.update();

        return this;
    },

    /*
     * Update the diff commit list table.
     *
     * This will populate the table with entries from the associated
     * DiffCommitCollection. If the collection is empty (i.e., the selected
     * diff revision has no commits associated with it), then the diff commit
     * list table will be hidden.
     *
     * It will also render diff complexity icons next to each commit showing
     * the complexity in terms of lines inserted, removed, and changed.
     */
    update: function() {
        var $tbody,
            renderHistorySymbol = _.any(
                this.collection.models,
                function(item) {
                    return item.get('historyEntrySymbol') != ' ';
                });

        this._$itemsTable.empty();

        if (this.collection.length > 0) {
            $tbody = $('<tbody/>');

            this.collection.each(function(diffCommit) {
                var lineCounts = diffCommit.attributes.lineCounts,
                    tr = this._itemTemplate(_.defaults(
                        {
                            renderHistorySymbol: renderHistorySymbol,
                            cid: diffCommit.cid
                        },
                        diffCommit.attributes)),
                    iconView = new RB.DiffComplexityIconView({
                        numInserts: lineCounts.inserted,
                        numDeletes: lineCounts.deleted,
                        numReplaces: lineCounts.replaced,
                        totalLines: diffCommit.getTotalLineCount()
                    });

                $tbody.append(tr);
                iconView.$el.appendTo($tbody.find('.diff-file-icon').last());
                iconView.render();
            }, this);

            this._$itemsTable.append(this._tableHeader(
                {
                    renderHistorySymbol: renderHistorySymbol
                }
            ));
            this._$itemsTable.append($tbody);

            /*
             * We can't handle the mouseleave event with the out parameter to
             * $.hoverIntent because we will be sticking another element in
             * front of the hovered over element. However, it still needs a
             * function to call when the mouseleave event happens, or it will
             * cause an error.
             */
            $tbody
                .find('.diff-commit-expandable-summary')
                .hoverIntent({
                    timeout: 500,
                    over: this._onExpandSummary,
                    out: function() {}
                });

            this.$el.show();
        } else {
            this.$el.hide();
        }
    },

    /*
     * Show an expanded description tooltip for a commit summary.
     */
    _onExpandSummary: function(event) {
        var $target = $(event.target),
            cid = $target.data('diff-commit-cid'),
            description = $.trim(this.collection.get(cid).get('description')),
            summary = $.trim(this.collection.get(cid).get('summary')),
            $tooltip,
            offset,
            left,
            top;

        if (description !== summary) {
            /*
             * We only have to show the tooltip when there is an extended
             * description to display.
             */
            offset = $target.offset();

            $tooltip = $('<div/>')
                .addClass('diff-commit-expanded-summary')
                .html(_.escape(description).replace(/\n/g, '<br>'))
                .hide()
                .on('mouseleave', function() {
                    $tooltip.fadeOut(500, function() {
                        $tooltip.remove();
                    });
                })
                .appendTo(this._$body);

            left = offset.left - $tooltip.getExtents('p', 'l')
                   - $target.getExtents('p', 'l');
            top = offset.top - $tooltip.getExtents('p', 't')
                  - $target.getExtents('p', 't') + $target.getExtents('b', 't')
                  + $tooltip.getExtents('b', 't') + 2;

            $tooltip
                .css({
                    left: left + 'px',
                    top: top + 'px'
                })
                .fadeIn();
        }
    }
});
