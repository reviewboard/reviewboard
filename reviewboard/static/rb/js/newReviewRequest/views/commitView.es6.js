/**
 * A view for a committed revision.
 *
 * This is used specifically for new review request creation. A click on the
 * element will either navigate the page to the review request (if one exists),
 * or emit a 'create' event.
 */
RB.CommitView = Backbone.View.extend({
    className: 'commit',

    /**
     * Template for the main view.
     */
    template: _.template(dedent`
        <div class="progress">
         <span class="fa fa-spinner fa-pulse"></span>
        </div>
        <% if (accessible) { %>
         <div class="summary">
          <% if (reviewRequestURL) { %>
           <span class="fa fa-arrow-circle-right jump-to-commit"/>
          <% } %>
          <%- summary %>
         </div>
        <% } %>
        <div class="commit-info">
         <span class="revision">
          <span class="fa fa-code-fork"></span>
          <%- revision %>
          <% if (!accessible) { %>
           <%- RB.CommitView.strings.COMMIT_NOT_ACCESSIBLE %>
          <% } %>
         </span>
         <% if (accessible && author) { %>
          <span class="author">
           <span class="fa fa-user"></span>
           <%- author %>
          </span>
         <% } %>
         <% if (date) { %>
          <span class="time">
           <span class="fa fa-clock-o"></span>
           <time class="timesince" datetime="<%- date %>"></time>
          </span>
         <% } %>
        </div>
    `),

    /**
     * Template for the body content of the confirmation dialog.
     */
    _dialogBodyTemplate: _.template(dedent`
        <p><%- prefixText %></p>
        <p><code><%- commitID %>: <%- summary %></code></p>
        <p><%- suffixText %></p>
    `),

    events: {
        'click': '_onClick',
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.CommitView:
     *     This object, for chaining.
     */
    render: function() {
        if (!this.model.get('accessible')) {
            this.$el.addClass('disabled');
        }

        let commitID = this.model.get('id');

        if (commitID.length === 40) {
            commitID = commitID.slice(0, 7);
        }

        if (this.model.get('reviewRequestURL')) {
            this.$el.addClass('has-review-request');
        }

        const date = this.model.get('date');

        this.$el.html(this.template(_.defaults({
            revision: commitID,
            author: this.model.get('authorName') || gettext('<unknown>'),
            date: date ? date.toISOString() : null,
        }, this.model.attributes)));

        if (date) {
            this.$('.timesince').timesince();
        }

        return this;
    },

    /**
     * Handler for when the commit is clicked.
     *
     * Shows a confirmation dialog allowing the user to proceed or cancel.
     */
    _onClick() {
        let commitID = this.model.get('id');

        if (commitID.length > 7) {
            commitID = commitID.slice(0, 7);
        }

        const dialogView = new RB.DialogView({
            title: gettext('Create Review Request?'),
            body: this._dialogBodyTemplate({
                prefixText: gettext('You are creating a new review request from the following published commit:'),
                commitID: commitID,
                summary: this.model.get('summary'),
                suffixText: gettext('Are you sure you want to continue?'),
            }),
            buttons: [
                {
                    id: 'cancel',
                    label: gettext('Cancel'),
                },
                {
                    id: 'create',
                    label: gettext('Create Review Request'),
                    primary: true,
                    onClick: this._createReviewRequest.bind(this),
                }
            ]
        });

        dialogView.show();
    },

    /**
     * Create a new review request for the selected commit.
     *
     * If a review request already exists for this commit, redirect the browser
     * to it. If not, trigger the 'create' event.
     */
    _createReviewRequest() {
        if (this.model.get('accessible')) {
            const url = this.model.get('reviewRequestURL');

            if (url) {
                window.location = url;
            } else {
                this.model.trigger('create', this.model);
            }
        }
    },

    /**
     * Toggle a progress indicator on for this commit.
     */
    showProgress() {
        this.$('.progress').show();
    },

    /**
     * Toggle a progress indicator off for this commit.
     */
    cancelProgress() {
        this.$('.progress').hide();
    },
}, {
    strings: {
        COMMIT_NOT_ACCESSIBLE: gettext('(not accessible on this repository)'),
    },
});
