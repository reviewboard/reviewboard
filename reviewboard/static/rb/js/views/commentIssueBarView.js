/*
 * Manages a comment's issue status bar.
 *
 * The buttons on the bar will update the comment's issue status on the server
 * when clicked. The bar will update to reflect the issue status of any
 * comments tracked by the issue summary table.
 */
RB.CommentIssueBarView = Backbone.View.extend({
    events: {
        'click .reopen': '_onReopenClicked',
        'click .resolve': '_onResolveClicked',
        'click .drop': '_onDropClicked'
    },

    STATUS_OPEN: 'open',
    STATUS_FIXED: 'resolved',
    STATUS_DROPPED: 'dropped',

    statusInfo: {
        open: {
            visibleButtons: ['.drop', '.resolve'],
            text: gettext('An issue was opened.')
        },
        resolved: {
            visibleButtons: ['.reopen'],
            text: gettext('The issue has been resolved.')
        },
        dropped: {
            visibleButtons: ['.reopen'],
            text: gettext('The issue has been dropped.')
        }
    },

    template: _.template([
        '<div class="issue-state">',
        ' <div class="issue-container">',
        '  <span class="rb-icon"></span>',
        '  <span class="issue-details">',
        '   <span class="issue-message"></span>',
        '<% if (interactive) { %>',
        '   <span class="issue-actions">',
        '    <input type="button" class="issue-button resolve" ',
        '           value="<%- fixedLabel %>" />',
        '    <input type="button" class="issue-button drop" ',
        '           value="<%- dropLabel %>" />',
        '    <input type="button" class="issue-button reopen" ',
        '           value="<%- reopenLabel %>" />',
        '   </span>',
        '<% } %>',
        '  </span>',
        ' </div>',
        '</div>'
    ].join('')),

    initialize: function() {
        this._manager = this.options.commentIssueManager ||
                        RB.PageManager.getPage().reviewRequestEditor
                            .get('commentIssueManager');
        this._issueStatus = this.options.issueStatus;
        this._$buttons = null;
        this._$state = null;
        this._$icon = null;
        this._$message = null;
    },

    /*
     * Renders the issue status bar.
     */
    render: function() {
        if (this.$el.children().length === 0) {
            this.$el.append(this.template({
                interactive: this.options.interactive,
                fixedLabel: gettext('Fixed'),
                dropLabel: gettext('Drop'),
                reopenLabel: gettext('Re-open')
            }));
        }

        this._$buttons = this.$('.issue-button');
        this._$state = this.$('.issue-state');
        this._$icon = this.$('.rb-icon');
        this._$message = this.$('.issue-message');

        this._manager.on('issueStatusUpdated',
                         this._onIssueStatusUpdated,
                         this);
        this._showStatus(this._issueStatus);

        return this;
    },

    /*
     * Sets the issue status of the comment on the server.
     */
    _setStatus: function(issueStatus) {
        this._$buttons.prop('disabled', true);
        this._manager.setCommentState(this.options.reviewID,
                                      this.options.commentID,
                                      this.options.commentType,
                                      issueStatus);
    },

    /*
     * Shows the current issue status of the comment.
     *
     * This will affect the button visibility and the text of the bar.
     */
    _showStatus: function(issueStatus) {
        var statusInfo = this.statusInfo[issueStatus],
            prevStatus = this._issueStatus;

        this._issueStatus = issueStatus;

        this._$state
            .removeClass(prevStatus)
            .addClass(issueStatus);

        this._$icon
            .removeClass('rb-icon-issue-' + prevStatus)
            .addClass('rb-icon-issue-' + issueStatus);

        this._$buttons.hide();
        this._$message.text(statusInfo.text);

        if (this.options.interactive) {
            this._$buttons.filter(statusInfo.visibleButtons.join(',')).show();
            this._$buttons.prop('disabled', false);
        }

        this.trigger('statusChanged', issueStatus);
    },

    /*
     * Handler for when "Re-open" is clicked.
     *
     * Reopens the issue.
     */
    _onReopenClicked: function() {
        this._setStatus(this.STATUS_OPEN);
    },

    /*
     * Handler for when "Fixed" is clicked.
     *
     * Marks the issue as fixed.
     */
    _onResolveClicked: function() {
        this._setStatus(this.STATUS_FIXED);
    },

    /*
     * Handler for when "Drop" is clicked.
     *
     * Marks the issue as dropped.
     */
    _onDropClicked: function() {
        this._setStatus(this.STATUS_DROPPED);
    },

    /*
     * Handler for when the issue status for the comment changes.
     *
     * Updates the dispaly to reflect the issue's current status.
     */
    _onIssueStatusUpdated: function(comment) {
        if (comment.id === this.options.commentID) {
            this._showStatus(comment.get('issueStatus'));
        }
    }
});
