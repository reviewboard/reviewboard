/**
 * Manages a comment's issue status bar.
 *
 * The buttons on the bar will update the comment's issue status on the server
 * when clicked. The bar will update to reflect the issue status of any
 * comments tracked by the issue summary table.
 */
RB.CommentIssueBarView = Backbone.View.extend({
    events: {
        'click .reopen': '_onReopenClicked',
        'click .resolve': '_onFixedClicked',
        'click .drop': '_onDropClicked',
        'click .verify-dropped': '_onVerifyDroppedClicked',
        'click .verify-resolved': '_onVerifyFixedClicked',
    },

    statusInfo: {
        open: {
            visibleButtons: ['.drop', '.resolve'],
            text: gettext('An issue was opened.'),
        },
        resolved: {
            visibleButtons: ['.reopen'],
            text: gettext('The issue has been resolved.'),
        },
        dropped: {
            visibleButtons: ['.reopen'],
            text: gettext('The issue has been dropped.'),
        },
        'verifying-dropped': {
            visibleButtons: ['.reopen'],
            text: gettext('Waiting for verification before dropping...'),
        },
        'verifying-resolved': {
            visibleButtons: ['.reopen'],
            text: gettext('Waiting for verification before resolving...'),
        },
    },

    template: _.template(dedent`
        <div class="issue-state">
         <div class="issue-container">
          <span class="rb-icon"></span>
          <span class="issue-details">
           <span class="issue-message"></span>
           <% if (interactive) { %>
            <span class="issue-actions">
             <input type="button" class="issue-button resolve"
                    value="<%- fixedLabel %>">
             <input type="button" class="issue-button drop"
                    value="<%- dropLabel %>">
             <input type="button" class="issue-button reopen"
                    value="<%- reopenLabel %>">
             <input type="button" class="issue-button verify-resolved"
                    value="<%- verifyFixedLabel %>">
             <input type="button" class="issue-button verify-dropped"
                    value="<%- verifyDroppedLabel %>">
            </span>
           <% } %>
          </span>
         </div>
        </div>
    `),

    /**
     * Initialize the view.
     *
     * Args:
     *     options (object):
     *         Options for the view.
     *
     * Option Args:
     *     canVerify (boolean):
     *         Whether the user has permission to verify issues that require
     *         it.
     *
     *     commentID (number):
     *         The ID of the comment object.
     *
     *     commentIssueManager (RB.CommentIssueManager):
     *         The issue manager.
     *
     *     commentType (string):
     *         The type of comment being modified.
     *
     *     interactive (boolean):
     *         Whether the comment issue bar is interactive or not.
     *
     *     issueStatus (string):
     *         The current issue status.
     *
     *     reviewID (number):
     *         The ID of the review that the comment is on.
     */
    initialize(options) {
        this.options = options;

        const page = RB.PageManager.getPage();

        this._manager = (this.options.commentIssueManager ||
                         page.model.commentIssueManager);
        this._issueStatus = this.options.issueStatus;
        this._$buttons = null;
        this._$state = null;
        this._$icon = null;
        this._$message = null;
    },

    /**
     * Render the issue status bar.
     *
     * Returns:
     *     RB.CommentIssueBarView:
     *     This object, for chaining.
     */
    render() {
        if (this.$el.children().length === 0) {
            this.$el.append(this.template({
                interactive: this.options.interactive,
                fixedLabel: gettext('Fixed'),
                dropLabel: gettext('Drop'),
                reopenLabel: gettext('Re-open'),
                verifyDroppedLabel: gettext('Verify Dropped'),
                verifyFixedLabel: gettext('Verify Fixed'),
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

    /**
     * Set the issue status of the comment on the server.
     *
     * Args:
     *     issueStatus (string):
     *         The new issue status (one of ``open``, ``resolved``, or
     *         ``dropped``).
     */
    _setStatus(issueStatus) {
        this._$buttons.prop('disabled', true);
        this._manager.setCommentState(this.options.reviewID,
                                      this.options.commentID,
                                      this.options.commentType,
                                      issueStatus);
    },

    /**
     * Show the current issue status of the comment.
     *
     * This will affect the button visibility and the text of the bar.
     *
     * Args:
     *     issueStatus (string):
     *         The issue status to show (one of ``open``, ``resolved``, or
     *         ``dropped``).
     */
    _showStatus(issueStatus) {
        const statusInfo = this.statusInfo[issueStatus];
        const prevStatus = this._issueStatus;

        this._issueStatus = issueStatus;

        this._$state
            .removeClass(prevStatus)
            .addClass(issueStatus);

        let iconClass;

        if (issueStatus === RB.BaseComment.STATE_VERIFYING_DROPPED ||
            issueStatus === RB.BaseComment.STATE_VERIFYING_RESOLVED) {
            iconClass = 'rb-icon rb-icon-issue-verifying';
        } else {
            iconClass = `rb-icon rb-icon-issue-${issueStatus}`;
        }

        this._$icon.attr('class', iconClass);
        this._$buttons.hide();
        this._$message.text(statusInfo.text);

        if (this.options.interactive) {
            let visibleButtons = statusInfo.visibleButtons;

            if (this.options.canVerify) {
                if (issueStatus === RB.BaseComment.STATE_VERIFYING_DROPPED) {
                    visibleButtons.push('.verify-dropped');
                } else if (issueStatus ===
                           RB.BaseComment.STATE_VERIFYING_RESOLVED) {
                    visibleButtons.push('.verify-resolved');
                }
            }

            this._$buttons.filter(visibleButtons.join(',')).show();
            this._$buttons.prop('disabled', false);
        }

        this.trigger('statusChanged', prevStatus, issueStatus);
    },

    /**
     * Handler for when "Re-open" is clicked.
     *
     * Reopens the issue.
     */
    _onReopenClicked() {
        this._setStatus(RB.BaseComment.STATE_OPEN);
    },

    /**
     * Handler for when "Fixed" is clicked.
     *
     * Marks the issue as fixed.
     */
    _onFixedClicked() {
        const comment = this._manager.getComment(this.options.reviewID,
                                                 this.options.commentID,
                                                 this.options.commentType);

        comment.ready({
            ready: () => {
                if (comment.requiresVerification() &&
                    comment.getAuthorUsername() !==
                        RB.UserSession.instance.get('username')) {
                    this._setStatus(RB.BaseComment.STATE_VERIFYING_RESOLVED);
                } else {
                    this._setStatus(RB.BaseComment.STATE_RESOLVED);
                }
            },
        });
    },

    /**
     * Handler for when "Drop" is clicked.
     *
     * Marks the issue as dropped.
     */
    _onDropClicked() {
        const comment = this._manager.getComment(this.options.reviewID,
                                                 this.options.commentID,
                                                 this.options.commentType);

        comment.ready({
            ready: () => {
                if (comment.requiresVerification() &&
                    comment.getAuthorUsername() !==
                        RB.UserSession.instance.get('username')) {
                    this._setStatus(RB.BaseComment.STATE_VERIFYING_DROPPED);
                } else {
                    this._setStatus(RB.BaseComment.STATE_DROPPED);
                }
            },
        });
    },

    /**
     * Handler for when "Verify Fixed" is clicked.
     */
    _onVerifyFixedClicked() {
        this._setStatus(RB.BaseComment.STATE_RESOLVED);
    },

    /**
     * Handler for when "Verify Dropped" is clicked.
     */
    _onVerifyDroppedClicked() {
        this._setStatus(RB.BaseComment.STATE_DROPPED);
    },

    /**
     * Handler for when the issue status for the comment changes.
     *
     * Updates the dispaly to reflect the issue's current status.
     *
     * Args:
     *     comment (RB.BaseComment):
     *         The comment model which was updated.
     */
    _onIssueStatusUpdated(comment) {
        if (comment.id === this.options.commentID) {
            this._showStatus(comment.get('issueStatus'));
        }
    },
});
