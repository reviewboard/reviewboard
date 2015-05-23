/*
 * The DiffCommitIndexView displays a table containing diff commit entries.
 *
 * The view contains all the commits associated with the diff revision selected
 * by the diff revision selector.
 */
RB.DiffCommitIndexView = Backbone.View.extend({
    events: {
        'click .base-diff-commit-selector:checked': '_onSelectBaseCommit',
        'click .tip-diff-commit-selector:checked': '_onSelectTipCommit'
    },

    /*
     * Initialize the view.
     */
    initialize: function(options) {
        this._$itemsTable = null;
        this._$body = $(document.body);
        this._baseCommit = null;
        this._tipCommit = null;

        this.collection = this.options.collection;
        this.listenTo(this.collection, 'update', this.update);

        if (options.baseCommitID !== undefined) {
            this._baseCommit = this.collection.findWhere({
                commitID: options.baseCommitID
            });
        }

        if (options.tipCommitID !== undefined) {
            this._tipCommit = this.collection.findWhere({
                commitID: options.tipCommitID
            });
        }

        _.bindAll(this, '_onExpandSummary');
    },

    _itemTemplate: _.template([
        '<tr class="commit-entry-<%- historyEntryType%>">',
        ' <% if (renderHistorySymbol) { %>',
        ' <td class="commit-entry-type"><%- historyEntrySymbol %></td>',
        ' <% } else if (renderCommitSelector) { %>',
        ' <%  if (renderBaseCommitSelector) { %>',
        ' <td>',
        '  <input type="radio" name="base-diff-commit-selector"',
        '         id="base-diff-commit-selector-<%- cid %>"',
        '         class="base-diff-commit-selector" value="<%- cid %>">',
        ' </td>',
        ' <%  } else { %>',
        ' <td></td>',
        ' <%  } %>',
        ' <td>',
        '  <input type="radio" name="tip-diff-commit-selector"',
        '         id="tip-diff-commit-selector-<%- cid %>"',
        '         class="tip-diff-commit-selector" value="<%- cid %>">',
        ' </td>',
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
        '  <% } else if (renderCommitSelector) { %>',
        '  <th>',
        '   <input type="radio" name="base-diff-commit-selector"',
        '          id="base-diff-commit-selector-none" value="none"',
        '          class="base-diff-commit-selector">',
        '  </th>',
        '  <th></th>',
        '  <% } %>',
        '  <th></th>',
        '  <th><%- summaryText %></th>',
        '  <th><%- authorText %></th>',
        ' </tr>',
        '</thead>'
    ].join('')),

    /*
     * Render the diff commit list table.
     */
    render: function(options) {
        this._$itemsTable = $('<table/>').appendTo(this.$el);

        this.update(options);

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
     *
     * Options is a JavaScript object that can take the following keys:
     *
     *  - update: Determines if the `_baseCommit` and `_tipCommit` members
     *            should be updated while rendering.
     */
    update: function(options) {
        var renderHistorySymbol = _.any(
                this.collection.models,
                function(item) {
                    return item.get('historyEntrySymbol') != ' ';
                }),
            itemCount = this.collection.size(),
            $radio,
            $tbody,
            shouldUpdate;

        options = options || {};
        shouldUpdate = options.update !== false;

        if (shouldUpdate) {
            this._baseCommit = null;
        }

        this._$itemsTable.empty();

        if (this.collection.length > 0) {
            $tbody = $('<tbody/>');

            this.collection.each(function(diffCommit, i) {
                var lineCounts = diffCommit.attributes.lineCounts,
                    lastCommit = i + 1 === itemCount,
                    tr = this._itemTemplate(_.defaults(
                        {
                            renderHistorySymbol: renderHistorySymbol,
                            renderBaseCommitSelector: !lastCommit,
                            renderCommitSelector: true,
                            cid: diffCommit.cid
                        },
                        diffCommit.attributes)),
                    iconView = new RB.DiffComplexityIconView({
                        numInserts: lineCounts.inserted,
                        numDeletes: lineCounts.deleted,
                        numReplaces: lineCounts.replaced,
                        totalLines: diffCommit.getTotalLineCount()
                    });

                if ((shouldUpdate || this._tipCommit == null) &&
                    lastCommit) {
                    this._tipCommit = diffCommit;
                }

                $tbody.append(tr);
                iconView.$el.appendTo($tbody.find('.diff-file-icon').last());
                iconView.render();
            }, this);

            this._$itemsTable.append(this._tableHeader(
                {
                    renderHistorySymbol: renderHistorySymbol,
                    renderCommitSelector: true,
                    authorText: gettext('Author'),
                    summaryText: gettext('Summary')
                }
            ));
            this._$itemsTable.append($tbody);

            if (this._baseCommit === null) {
                $radio = this._$itemsTable
                    .find('#base-diff-commit-selector-none')
                    .prop({checked: true});
            } else {
                $radio = this._$itemsTable
                    .find('#base-diff-commit-selector-' + this._baseCommit.cid)
                    .prop({checked: true});
            }

            this._onSelectBaseCommit({target: $radio}, false);

            $radio = this._$itemsTable
                .find('#tip-diff-commit-selector-' + this._tipCommit.cid)
                .prop({checked: true});

            this._onSelectTipCommit({target: $radio}, false);

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
    },

    /*
     * Handle the base commit being selected.
     *
     * This disables the radio buttons for the end DiffCommit that would result
     * in an invalid commit range.
     */
    _onSelectBaseCommit: function(ev, trigger) {
        var $target = $(ev.target),
            $radios = this.$('.tip-diff-commit-selector'),
            cid = $target.prop('value'),
            index;

        if (cid !== 'none') {
            this._baseCommit = this.collection.get(cid);
            index = this.collection.indexOf(this._baseCommit);

            $radios.slice(0, index + 1).prop('disabled', true);
            $radios.slice(index + 1).prop(
                'disabled', false);
        } else {
            this._baseCommit = null;
            $radios.prop('disabled', false);
        }

        if (trigger !== false) {
            this.trigger('diffCommitsChanged', {
                base: this._baseCommit,
                tip: this._tipCommit
            });
        }
    },

    /*
     * Handle the tip commit being selected.
     *
     * This disables the radio buttons for base DiffCommit that would result
     * in an invalid commit range.
     */
    _onSelectTipCommit: function(ev, trigger) {
        var $target = $(ev.target),
            $radios = this.$('.base-diff-commit-selector'),
            cid = $target.prop('value'),
            commit = this.collection.get(cid),
            index = this.collection.indexOf(commit);

        $radios.slice(0, index + 1).prop('disabled', false);
        $radios.slice(index + 1).prop('disabled', true);

        this._tipCommit = commit;

        if (trigger !== false) {
            this.trigger('diffCommitsChanged', {
                base: this._baseCommit,
                tip: this._tipCommit
            });
        }
    }
});
