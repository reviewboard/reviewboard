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
    <tr class="<%- rowClass %>">
     <% if (showHistorySymbol) { %>
      <td class="marker">
       <%- historyDiffEntry.getSymbol() %>
      </td>
     <% } %>
     <% if (showExpandCollapse) { %>
      <td>
       <% if (commit.hasSummary()) { %>
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
      <pre><%- commit.get('summary') %></pre>
     </td>
     <td<% if (showHistorySymbol) { %> class="value"<% } %>>
       <%- commit.get('authorName') %>
     </td>
    </tr>
`);

const headerTemplate = _.template(dedent`
    <thead>
     <tr>
      <% if (showHistorySymbol) { %>
       <th></th>
      <% } %>
      <th<% if (showExpandCollapse) { %> colspan="2"<% } %>>
       <%- summaryText %>
       </th>
      <th><%- authorText %></th>
     </tr>
    </thead>
`);

const tableTemplate = _.template(dedent`
    <table class="commit-list">
     <colgroup>
      <% if (showHistorySymbol) { %>
       <col>
      <% } %>
      <% if (showExpandCollapse) { %>
       <col class="expand-collapse-control">
      <% } %>
      <col>
      <col>
     </colgroup>
    </table>
`);

/**
 * A view for displaying a list of commits and their metadata.
 */
RB.DiffCommitListView = Backbone.View.extend({
    events: {
        'click .collapse-commit-message': '_collapseCommitMessage',
        'click .expand-commit-message': '_expandCommitMessage',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        this.listenTo(this.model.get('commits'), 'reset', this.render);
        this.listenTo(this.model, 'change:isInterdiff', this.render);
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
        const isInterdiff =  this.model.isInterdiff();

        const commonContext = {
            showExpandCollapse: commits.some(commit => commit.hasSummary()),
            showHistorySymbol: isInterdiff,
        };

        const $content = $(tableTemplate(commonContext))
            .toggleClass('changed', isInterdiff)
            .append(headerTemplate(_.extend(
                {
                    authorText: gettext('Author'),
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
            commits.each(commit => $tbody.append(itemTemplate(_.extend(
                {
                    commit: commit,
                },
                commonContext
            ))));
        }

        $content.append($tbody);

        this.$el
            .empty()
            .append($content);

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
});


})();
