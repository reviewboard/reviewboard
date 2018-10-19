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
    <tr<% if (rowClass) { %> class="<%- rowClass %>"<% } %>>
     <% if (showHistorySymbol) { %>
      <td class="marker">
       <%- historyDiffEntry.getSymbol() %>
      </td>
     <% } else if (showInterCommitDiffControls) { %>
      <td class="select-base">
       <input type="radio"
              class="base-commit-selector"
              name="base-commit-id"
              <% if (baseSelected) { %>checked<% } %>
              <% if (baseDisabled) { %>disabled<% } %>
              value="<%- commit.id %>">
      </td>
      <td class="select-tip">
       <input type="radio"
              class="tip-commit-selector"
              name="tip-commit-id"
              <% if (tipSelected) { %>checked<% } %>
              <% if (tipDisabled) { %>disabled<% } %>
              value="<%- commit.id %>">
      </td>
     <% } %>
     <% if (showExpandCollapse) { %>
      <td>
       <% if (commit && commit.hasSummary()) { %>
        <a href="#"
           class="expand-commit-message"
           data-commit-id="<%- commit.id %>"
           aria-role="button">
         <span class="fa fa-plus" title="<%- expandText %>"></span>
        </a>
       <% } %>
      </td>
     <% } %>
     <td<% if (showHistorySymbol) { %> class="value"<% } %>>
      <% if (commit !== null) { %>
       <pre><%- commit.get('summary') %></pre>
      <% } %>
     </td>
     <td<% if (showHistorySymbol) { %> class="value"<% } %>>
      <% if (commit !== null) { %>
       <%- commit.get('authorName') %>
      <% } %>
     </td>
    </tr>
`);

const headerTemplate = _.template(dedent`
    <thead>
     <tr>
      <% if (showHistorySymbol) { %>
       <th></th>
      <% } else if (showInterCommitDiffControls) { %>
       <th><%- firstText %></th>
       <th><%- lastText %></th>
      <% } %>
      <th<% if (showExpandCollapse) { %> colspan="2"<% } %>>
       <%- summaryText %>
       </th>
      <th><%- authorText %></th>
     </tr>
    </thead>
`);

const tableTemplate = _.template(dedent`
    <form>
     <table class="commit-list">
      <colgroup>
       <% if (showHistorySymbol) { %>
        <col>
       <% } else if (showInterCommitDiffControls) { %>
         <col>
         <col>
       <% } %>
       <% if (showExpandCollapse) { %>
        <col class="expand-collapse-control">
       <% } %>
       <col>
       <col>
      </colgroup>
     </table>
    </form>
`);

/**
 * A view for displaying a list of commits and their metadata.
 */
RB.DiffCommitListView = Backbone.View.extend({
    events: {
        'change .base-commit-selector': '_onBaseChanged',
        'change .tip-commit-selector': '_onTipChanged',
        'click .collapse-commit-message': '_collapseCommitMessage',
        'click .expand-commit-message': '_expandCommitMessage',
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
            showExpandCollapse: commits.some(commit => commit.hasSummary()),
            showHistorySymbol: isInterdiff,
            showInterCommitDiffControls:
                this._showInterCommitDiffControls,
        };

        const $content = $(tableTemplate(commonContext))
        const $table = $content
            .find('table')
            .toggleClass('changed', isInterdiff)
            .append(headerTemplate(_.extend(
                {
                    authorText: gettext('Author'),
                    firstText: gettext('First'),
                    lastText: gettext('Last'),
                    summaryText: gettext('Summary'),
                },
                commonContext
            )));

        const $tbody = $('<tbody />');

        commonContext.expandText = gettext('Expand commit message.');

        if (isInterdiff) {
            this.model.get('historyDiff').each(historyDiffEntry => {
                const entryType = historyDiffEntry.get('entryType');

                let key;
                let rowClass;

                switch (entryType) {
                    case RB.CommitHistoryDiffEntry.ADDED:
                        rowClass = 'new-value';
                        key = 'newCommitID';
                        break;

                    case RB.CommitHistoryDiffEntry.REMOVED:
                        rowClass = 'old-value';
                        key = 'oldCommitID';
                        break;

                    case RB.CommitHistoryDiffEntry.UNMODIFIED:
                    case RB.CommitHistoryDiffEntry.MODIFIED:
                        key = 'newCommitID';
                        break;

                    default:
                        console.error('Invalid history entry type: %s',
                                      entryType);
                        break;
                }

                const commit = commits.get(historyDiffEntry.get(key));

                $tbody.append(itemTemplate(_.extend(
                    {
                        commit: commit,
                        historyDiffEntry: historyDiffEntry,
                        rowClass: rowClass,
                    },
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
                        commit: commit,
                        baseSelected: i === baseIndex,
                        tipSelected: i === tipIndex,
                        baseDisabled: i > tipIndex,
                        tipDisabled: i < baseIndex,
                    },
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
     * Handle the expand button being clicked.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event.
     */
    _expandCommitMessage(e) {
        e.preventDefault();
        e.stopPropagation();

        this._expandOrCollapse(
            $(e.target).closest('.expand-commit-message'),
            true);
    },

    /**
     * Handle the collapse button being clicked.
     *
     * Args:
     *     e (jQuery.Event):
     *         The click event.
     */
    _collapseCommitMessage(e) {
        e.preventDefault();
        e.stopPropagation();

        this._expandOrCollapse(
            $(e.target).closest('.collapse-commit-message'),
            false);
    },

    /**
     * Expand or collapse the commit message on the same row as the link.
     *
     * Args:
     *     $link (jQuery):
     *         The expand or collapse link that was clicked.
     *
     *     expand (boolean):
     *         Whether we are expanding (``true``) or collapsing (``false``).
     */
    _expandOrCollapse($link, expand) {
        const $icon = $link.find('.fa');
        const commitID = $link.data('commitId');

        const commit = this.model.get('commits').get(commitID);
        const newText = commit.get(expand ? 'commitMessage' : 'summary');

        $link.closest('tr')
            .find('pre')
            .text(newText);

        $link.attr(
            'class',
            expand ? 'collapse-commit-message' : 'expand-commit-message');

        $icon.attr({
            'class': expand ? 'fa fa-minus' : 'fa fa-plus',
            'title': expand ? gettext('Collapse commit message.')
                            : gettext('Expand commit message.'),
        });
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
