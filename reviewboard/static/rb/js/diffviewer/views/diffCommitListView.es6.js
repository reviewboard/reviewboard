/*
 * The templates should be kept in sync with:
 *
 * - templates/reviews/changedesc_commit_list.html
 * - templates/reviews/commit_list_field.html
 *
 * so that they render items identically.
 */
(function() {


const itemTemplate = _.template(dedent`
    <tr class="rb-c-commit-list__commit <%- rowClass || '' %>">
     <% if (showHistorySymbol) { %>
      <td class="rb-c-commit-list__op" aria-label="<%- opLabel %>"></td>
     <% } else if (showInterCommitDiffControls) { %>
      <td class="rb-c-commit-list__select-base">
       <input type="radio"
              class="base-commit-selector"
              name="base-commit-id"
              aria-label="<%- baseSelectorLabel %>"
              <% if (baseSelected) { %>checked<% } %>
              <% if (baseDisabled) { %>disabled<% } %>
              value="<%- commit.id %>">
      </td>
      <td class="rb-c-commit-list__select-tip">
       <input type="radio"
              class="tip-commit-selector"
              name="tip-commit-id"
              aria-label="<%- tipSelectorLabel %>"
              <% if (tipSelected) { %>checked<% } %>
              <% if (tipDisabled) { %>disabled<% } %>
              value="<%- commit.id %>">
      </td>
     <% } %>
     <% if (commit) { %>
      <td class="rb-c-commit-list__message">
       <% if (commitBody) { %>
        <details>
         <summary class="rb-c-commit-list__message-summary"><%-
          commitSummary
         %></summary>
         <div class="rb-c-commit-list__message-body"><%- commitBody %></div>
        </details>
       <% } else { %>
        <div class="rb-c-commit-list__message-summary"><%-
         commitSummary
        %></div>
       <% } %>
      </td>
      <td class="rb-c-commit-list__id"
          title="<%- commitID %>"><%- commitID %></td>
      <td class="rb-c-commit-list__author"><%- commitAuthor %></td>
     <% } else { %>
      <td class="rb-c-commit-list__message"></td>
      <td class="rb-c-commit-list__id"></td>
      <td class="rb-c-commit-list__author"></td>
     <% } %>
    </tr>
`);

const headerTemplate = _.template(dedent`
    <thead>
     <tr>
      <% if (showHistorySymbol) { %>
       <th class="rb-c-commit-list__column-op"></th>
      <% } else if (showInterCommitDiffControls) { %>
       <th class="rb-c-commit-list__column-select-tip"><%- firstText %></th>
       <th class="rb-c-commit-list__column-select-base"><%- lastText %></th>
      <% } %>
      <th class="rb-c-commit-list__column-summary"><%- summaryText %></th>
      <th class="rb-c-commit-list__column-id"><%- idText %></th>
      <th class="rb-c-commit-list__column-author"><%- authorText %></th>
     </tr>
    </thead>
`);

const tableTemplate = _.template(dedent`
    <form class="rb-c-review-request-field-tabular rb-c-commit-list">
     <table class="rb-c-review-request-field-tabular__data"></table>
    </form>
`);

/**
 * A view for displaying a list of commits and their metadata.
 */
RB.DiffCommitListView = Backbone.View.extend({
    events: {
        'change .base-commit-selector': '_onBaseChanged',
        'change .tip-commit-selector': '_onTipChanged',
    },

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options that control how this view behaves.
     *
     * Option Args:
     *     showInterCommitDiffControls (boolean):
     *         Whether or not to show interdiff controls.
     */
    initialize(options) {
        this.listenTo(this.model.get('commits'), 'reset', this.render);

        this._showInterCommitDiffControls =
            !!options.showInterCommitDiffControls;

        this._$baseSelectors = $();
        this._$tipSelectors = $();
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.DiffCommitListView:
     *     This view, for chaining.
     */
    render() {
        const commits = this.model.get('commits');
        const isInterdiff = this.model.isInterdiff();

        const commonContext = {
            baseSelectorLabel: _`Set first commit`,
            showHistorySymbol: isInterdiff,
            showInterCommitDiffControls: this._showInterCommitDiffControls,
            tipSelectorLabel: _`Set last commit`,
        };

        const $content = $(tableTemplate(commonContext))
        const $table = $content
            .find('.rb-c-review-request-field-tabular__data')
            .append(headerTemplate(_.extend(
                {
                    authorText: _`Author`,
                    firstText: _`First`,
                    idText: _`ID`,
                    lastText: _`Last`,
                    summaryText: _`Summary`,
                },
                commonContext
            )));

        const $tbody = $('<tbody />');

        if (isInterdiff) {
            this.model.get('historyDiff').each(historyDiffEntry => {
                const entryType = historyDiffEntry.get('entryType');

                let key;
                let rowClass;
                let opLabel;

                switch (entryType) {
                    case RB.CommitHistoryDiffEntry.ADDED:
                        rowClass = '-is-added';
                        key = 'newCommitID';
                        opLabel = _`Added commit`;
                        break;

                    case RB.CommitHistoryDiffEntry.REMOVED:
                        rowClass = '-is-removed';
                        key = 'oldCommitID';
                        opLabel = _`Removed commit`;
                        break;

                    case RB.CommitHistoryDiffEntry.UNMODIFIED:
                        key = 'newCommitID';
                        opLabel = _`Added commit`;
                        break;

                    case RB.CommitHistoryDiffEntry.MODIFIED:
                        rowClass = '-is-modified';
                        key = 'newCommitID';
                        opLabel = _`Unmodified commit`;
                        break;

                    default:
                        console.error('Invalid history entry type: %s',
                                      entryType);
                        break;
                }

                const commit = commits.get(historyDiffEntry.get(key));

                $tbody.append(itemTemplate(_.extend(
                    {
                        historyDiffEntry: historyDiffEntry,
                        opLabel: opLabel,
                        rowClass: rowClass,
                    },
                    this._buildItemCommitContext(commit),
                    commonContext
                )));
            });
        } else {
            commonContext.rowClass = '';

            const baseCommitID = this.model.get('baseCommitID');
            const tipCommitID = this.model.get('tipCommitID');
            const lastIndex = commits.size() - 1;

            const baseIndex = (
                baseCommitID === null
                ? 0
                : commits.indexOf(commits.getChild(commits.get(baseCommitID)))
            );

            const tipIndex = (tipCommitID === null
                              ? lastIndex
                              : commits.indexOf(commits.get(tipCommitID)));

            commits.each((commit, i) => {
                $tbody.append(itemTemplate(_.extend(
                    {
                        baseSelected: i === baseIndex,
                        tipSelected: i === tipIndex,
                        baseDisabled: i > tipIndex,
                        tipDisabled: i < baseIndex,
                    },
                    this._buildItemCommitContext(commit),
                    commonContext
                )));
            });
        }

        $table.append($tbody);

        this.$el
            .empty()
            .append($content);

        this._$baseSelectors = this.$('.base-commit-selector');
        this._$tipSelectors = this.$('.tip-commit-selector');

        return this;
    },

    /**
     * Return template render context for a commit item.
     *
     * Args:
     *     commit (RB.DiffCommit):
     *         The commit for which to return context.
     *
     * Returns:
     *     object:
     *     The template render context for the item.
     */
    _buildItemCommitContext(commit) {
        let commitAuthor = null;
        let commitID = null;
        let commitSummary = null;
        let commitBody = null;

        if (commit) {
            commitAuthor = commit.get('authorName');
            commitID = commit.get('commitID');
            commitSummary = commit.get('summary');
            commitBody = commit.get('commitMessageBody');
        }

        return {
            commit: commit,
            commitAuthor: commitAuthor,
            commitBody: commitBody,
            commitID: commitID,
            commitSummary: commitSummary,
        };
    },

    /**
     * Handle the base commit selection changing.
     *
     * The view's model will be updated to reflect this change.
     *
     * Args:
     *     e (jQuery.Event):
     *         The change event.
     */
    _onBaseChanged(e) {
        const $target = $(e.target);
        const commits = this.model.get('commits');
        const commit = commits.get(parseInt($target.val(), 10));
        const index = commits.indexOf(commit);

        this.model.set('baseCommitID',
                       index === 0
                       ? null
                       : commits.getParent(commit).id);

        this._$tipSelectors
            .slice(0, index)
            .prop('disabled', true);

        this._$tipSelectors
            .slice(index)
            .prop('disabled', false);
    },

    /**
     * Handle the tip commit selection changing.
     *
     * The view's model will be updated to reflect this change.
     *
     * Args:
     *     e (jQuery.Event):
     *         The change event.
     */
    _onTipChanged(e) {
        const $target = $(e.target);
        const commits = this.model.get('commits');
        const commit = commits.get(parseInt($target.val(), 10));
        const index = commits.indexOf(commit);

        this.model.set('tipCommitID',
                       index === commits.size() - 1
                       ? null
                       : commit.id);

        this._$baseSelectors
            .slice(0, index + 1)
            .prop('disabled', false);

        this._$baseSelectors
            .slice(index + 1)
            .prop('disabled', true);
    },
});


})();
