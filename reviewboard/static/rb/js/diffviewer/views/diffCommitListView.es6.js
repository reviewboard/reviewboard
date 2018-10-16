/*
 * The templates should be kept in sync with:
 *
 * - template/reviews/commit_list_field.html
 *
 * so that they render items identically.
 */
(function() {


const itemTemplate = _.template(dedent`
    <tr>
     <% if (showExpandCollapse) { %>
      <td>
       <% if (commit.hasSummary()) { %>
        <a href="#"
           class="expand-commit-message"
           data-commit-id="<%- commit.get('commitID') %>"
           aria-role="button">
         <span class="fa fa-plus" title="<%- expandText %>"></span>
        </a>
       <% } %>
      </td>
     <% } %>
     <td><pre><%- commit.get('summary') %></pre></td>
     <td><%- commit.get('authorName') %></td>
    </tr>
`);

const headerTemplate = _.template(dedent`
    <thead>
     <tr>
      <% if (showExpandCollapse) { %>
       <th></th>
      <% } %>
      <th><%- summaryText %></th>
      <th><%- authorText %></th>
     </tr>
    </thead>
`);

const tableTemplate = _.template(dedent`
    <table class="commit-list">
     <colgroup>
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
        let $content;

        if (this.model.get('isInterdiff')) {
            /*
             * TODO: We should display the difference between the two sets of
             * commits.
             */
            $content = $('<p />')
                .text(gettext('Interdiff commit listings not supported.'));
        } else {
            const commits = this.model.get('commits');
            const showExpandCollapse = commits.some(
                commit => commit.hasSummary());

            $content =
                $(tableTemplate({
                    showExpandCollapse: showExpandCollapse,
                }))
                .append(headerTemplate({
                    authorText: gettext('Author'),
                    showExpandCollapse: showExpandCollapse,
                    summaryText: gettext('Summary'),
                }));

            const $tbody = $('<tbody />');

            commits.each(commit => $tbody.append(itemTemplate({
                expandText: gettext('Expand commit message.'),
                commit: commit,
                showExpandCollapse: showExpandCollapse,
            })));

            $content.append($tbody);
        }

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

        const commit = this.model.get('commits').findWhere({commitID});
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
