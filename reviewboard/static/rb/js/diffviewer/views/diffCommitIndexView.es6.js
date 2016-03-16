/**
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

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         The view options.
     *
     * Option Args:
     *     collection (RB.DiffCommitCollection):
     *         The collection of commits.
     *
     *     baseCommitID (string):
     *         An optional base commit ID for rendering an interdiff between
     *         two commits.
     *
     *     tipCommitID (string):
     *         An optional tip commit ID for rendering an interdiff between
     *         two commits.
     */
    initialize(options) {
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

        _.bindAll(this, '_tryExpandSummaryDelayed');
    },

    _itemTemplate: _.template(`
        <tr class="commit-entry-<% historyEntryType %>">
         <% if (renderHistorySymbol) { %>
          <td class="commit-entry-type"><%- historyEntrySymbol %></td>
         <% } else if (renderCommitSelector) { %>
          <% if (renderBaseCommitSelector) { %>
           <td>
            <input type="radio" name="base-diff-commit-selector"
                   id="base-diff-commit-selector-<%- cid %>"
                   class="base-diff-commit-selector" value="<%- cid %>">
           </td>
          <% } else { %>
           <td></td>
          <% } %>
          <td>
           <input type="radio" name="tip-diff-commit-selector"
                  id="tip-diff-commit-selector-<%- cid %>"
                  class="tip-diff-commit-selector" value="<%- cid %>">
          </td>
         <% } %>
         <td class="diff-file-icon"></td>
         <td class="<%- sumaryClasses.join(' ') %>"
             data-diff-commit-cid="<%- cid %>">
          <%- summary %>
         </td>
         <td class="diff-commit-author"><%- authorName %></td>
        </tr>
    `),

    _tableHeader: _.template(`
        <thead>
         <tr>
          <% if (renderHistorySymbol) { %>
           <th></th>
          <% } else if (renderCommitSelector) { %>
           <th>
            <input type="radio" name="base-diff-commit-selector"
                   id="base-diff-commit-selector-none" value="none"
                   class="base-diff-commit-selector">
           </th>
           <th></th>
          <% } %>
          <th></th>
          <th><%- summaryText %></th>
          <th><%- authorText %></th>
         </tr>
        </thead>
    `),

    /*
     * Render the diff commit list table.
     */
    render(options) {
        this._$itemsTable = $('<table/>').appendTo(this.$el);

        this.update(options);

        return this;
    },

    /**
     * Return if the shown commit history is from an interdiff.
     *
     * Returns:
     *     boolean: If the current commit history is from an interdiff or not.
     */
    isShowingInterdiff() {
        return this.collection.any(
            model => model.get('historyEntrySymbol') !== ' ');
    },

    /**
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
     * Args:
     *     options (object):
     *         Update options.
     *
     * Option Args:
     *     update (boolean):
     *         Determines if the ``_baseCommit`` and ``_tipCommit`` attributes
     *         should be updated while rendering.
     *
     * Returns:
     *     RB.DiffCommitIndexView:
     *     This object (for chaining).
     */
    update: function(options={}) {
        const renderHistorySymbol = this.isShowingInterdiff();
        const itemCount = this.collection.size();
        const shouldUpdate = options.update !== false;

        if (shouldUpdate) {
            this._baseCommit = null;
        }

        this._$itemsTable.empty();

        if (this.collection.length > 0) {
            const $tbody = $('<tbody/>');

            for (let [i, diffCommit] of Array.entries(this.collection.models)) {
                const lineCounts = diffCommit.attributes.lineCounts;
                const lastCommit = (i + 1 === itemCount);
                const summaryClasses = ['diff-commit-summary'];

                if (diffCommit.isSummarized()) {
                    summaryClasses.push('diff-commit-expandable-summary');
                }

                if ((shouldUpdate || this._tipCommit === null) && lastCommit) {
                    this._tipCommit = diffCommit;
                }

                const tr = this._itemTemplate(_.defaults({
                    renderHistorySymbol: renderHistorySymbol,
                    renderBaseCommitSelector: !lastCommit,
                    renderCommitSelector: true,
                    cid: diffCommit.cid,
                    summaryClasses: summaryClasses
                }, diffCommit.attributes));

                const iconView = new RB.DiffComplexityIconView({
                    numInserts: lineCounts.inserted,
                    numDeletes: lineCounts.deleted,
                    numReplaces: lineCounts.replaced,
                    totalLines: diffCommit.getTotalLineCount()
                });


                $tbody.append(tr);
                iconView.$el.appendTo($tbody.find('.diff-file-icon').last());
                iconView.render();
            }

            this._$itemsTable
                .append(this._tableHeader({
                    renderHistorySymbol: renderHistorySymbol,
                    renderCommitSelector: true,
                    authorText: gettext('Author'),
                    summaryText: gettext('Summary')
                }))
                .append($tbody);

            let $radio;

            if (this._baseCommit === null) {
                $radio = this._$itemsTable
                    .find('#base-diff-commit-selector-none')
                    .prop({checked: true});
            } else {
                $radio = this._$itemsTable
                    .find(`#base-diff-commit-selector-${this._baseCommit.cid}`)
                    .prop({checked: true});
            }

            this._onSelectBaseCommit({target: $radio}, false);

            $radio = this._$itemsTable
                .find(`#tip-diff-commit-selector-${this._tipCommit.cid}`)
                .prop({checked: true});

            this._onSelectTipCommit({target: $radio}, false);

            $tbody
                .find('.diff-commit-expandable-summary')
                .hover(this._tryExpandSummaryDelayed);

            this.$el.show();
        } else {
            this.$el.hide();
        }
    },

    /**
     * Return the range of selected commits.
     *
     * Returns:
     *     object:
     *     The commit range as an object with the following keys:
     *         ``base`` (RB.DiffCommit):
     *             The base commit.
     *
     *         ``tip`` (RB.DiffCommit):
     *             The tip commit.
     *
     *     When there is no range selected, ``null`` is returned instead.
     */
    getSelectedRange() {
        if (this.collection.size() === 0 || this.isShowingInterdiff()) {
            return null;
        }

        return {
            base: this._baseCommit,
            tip: this._tipCommit
        };
    },

    /*
     * Return the distance between two commits in the history.
     *
     * The distance is the length of the shortest path between them.
     *
     * TODO: This only supports linear histories.
     *
     * Args:
     *     a (RB.DiffCommit):
     *         The first commit to compare.
     *
     *     b (RB.DiffCommit):
     *         The second commit to compare.
     *
     * Returns:
     *     number: The distance between the two commits in the history.
     *
     */
    getDistance(a, b) {
        const indexA = this.collection.models.indexOf(a);
        const indexB = this.collection.models.indexOf(b);

        if (indexA === undefined || indexB === undefined) {
            return undefined;
        }

        return Math.abs(indexA - indexB);
    },

    /**
     * Show an expanded description tooltip for a commit summary.
     *
     * Args:
     *     $summary (jQuery):
     *         The summary to expand.
     */
    _expandSummary($summary) {
        const cid = $summary.data('diff-commit-cid');
        const description = $.trim(this.collection.get(cid).get('description'));
        const summary = $.trim(this.collection.get(cid).get('summary'));
        const offset = $summary.offset();
        const $tooltip = $('<div/>')
            .addClass('diff-commit-expanded-summary')
            .html(_.escape(description).replace(/\n/g, '<br>'))
            .hide()
            .on('mouseleave', () => {
                $tooltip.fadeOut(500, () => $tooltip.remove());
            })
            .appendTo(this._$body);
        const left = offset.left - $tooltip.getExtents('p', 'l')
                     - $summary.getExtents('p', 'l');
        const top = offset.top - $tooltip.getExtents('p', 't')
                    - $summary.getExtents('p', 't')
                    + $summary.getExtents('b', 't')
                    + $tooltip.getExtents('b', 't') + 2;

        $tooltip
            .css({
                left: left + 'px',
                top: top + 'px'
            })
            .fadeIn();
    },

    /**
     * Expand the summary after a delay if the user is still hovering over the
     * target.
     *
     * Args:
     *     e (Event):
     *         The event that triggered this.
     */
    _tryExpandSummaryDelayed(e) {
        const $target = $(e.target);

        _.delay(() => {
            if (target.is(':hover')) {
                this._expandSummary($target)
            }
        }, 500);
    },

    /**
     * Handle the base commit being selected.
     *
     * This disables the radio buttons for the end DiffCommit that would result
     * in an invalid commit range.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered this.
     *
     *     trigger (boolean):
     *         Whether or not this should trigger a ``diffCommitsChanged``
     *         event. This defaults to ``true``.
     */
    _onSelectBaseCommit(ev, trigger=true) {
        const $target = $(ev.target);
        const $radios = this.$('.tip-diff-commit-selector');
        const cid = $target.prop('value');

        if (cid !== 'none') {
            this._baseCommit = this.collection.get(cid);
            const index = this.collection.indexOf(this._baseCommit);

            $radios.slice(0, index + 1).prop('disabled', true);
            $radios.slice(index + 1).prop('disabled', false);
        } else {
            this._baseCommit = null;
            $radios.prop('disabled', false);
        }

        if (trigger) {
            this.trigger('diffCommitsChanged', this.getSelectedRange());
        }
    },

    /**
     * Handle the tip commit being selected.
     *
     * This disables the radio buttons for base DiffCommit that would result
     * in an invalid commit range.
     *
     * Args:
     *     ev (Event):
     *         The event that triggered this.
     *
     *     trigger (boolean):
     *         Whether or not this should trigger a ``diffCommitsChanged``
     *         event. This defaults to ``true``.
     */
    _onSelectTipCommit(ev, trigger=true) {
        const $target = $(ev.target);
        const $radios = this.$('.base-diff-commit-selector');
        const cid = $target.prop('value');
        const commit = this.collection.get(cid);
        const index = this.collection.indexOf(commit);

        $radios.slice(0, index + 1).prop('disabled', false);
        $radios.slice(index + 1).prop('disabled', true);

        this._tipCommit = commit;

        if (trigger) {
            this.trigger('diffCommitsChanged', this.getSelectedRange());
        }
    }
});
