/*
 * A view for a committed revision.
 *
 * This is used specifically for new review request creation. A click on the
 * element will either navigate the page to the review request (if one exists),
 * or emit a 'create' event.
 */
RB.CommitView = Backbone.View.extend({
    className: 'commit',

    template: _.template([
        '<div class="progress">',
        ' <span class="fa fa-spinner fa-pulse"></span>',
        '</div>',
        '<% if (accessible) { %>',
        ' <div class="summary">',
        '  <% if (reviewRequestURL) { %>',
        '   <span class="fa fa-arrow-circle-right jump-to-commit"/>',
        '  <% } %>',
        '  <%- summary %>',
        ' </div>',
        '<% } %>',
        '<div class="commit-info">',
        ' <span class="revision">',
        '  <span class="fa fa-code-fork"></span>',
        '  <%- revision %>',
        '  <% if (!accessible) { %>',
        '   <%- RB.CommitView.strings.COMMIT_NOT_ACCESSIBLE %>',
        '  <% } %>',
        ' </span>',
        ' <% if (accessible && author) { %>',
        '  <span class="author">',
        '   <span class="fa fa-user"></span>',
        '   <%- author %>',
        '  </span>',
        ' <% } %>',
        ' <% if (date) { %>',
        '  <span class="time">',
        '   <span class="fa fa-clock-o"></span>',
        '   <time class="timesince" datetime="<%- date %>"></time>',
        '  </span>',
        ' <% } %>',
        '</div>'
    ].join('')),

    events: {
        'click': '_onClick'
    },

    /*
     * Render the view.
     */
    render: function() {
        var commitID = this.model.get('id'),
            date = this.model.get('date');

        if (!this.model.get('accessible')) {
            this.$el.addClass('disabled');
        }

        if (commitID.length === 40) {
            commitID = commitID.slice(0, 7);
        }

        if (this.model.get('reviewRequestURL')) {
            this.$el.addClass('has-review-request');
        }

        this.$el.html(this.template(_.defaults({
            revision: commitID,
            author: this.model.get('authorName') || gettext('<unknown>'),
            date: date ? date.toISOString() : null
        }, this.model.attributes)));

        if (date) {
            this.$('.timesince').timesince();
        }

        return this;
    },

    /*
     * Handler for when the commit is clicked.
     *
     * If a review request already exists for this commit, redirect the browser
     * to it. If not, trigger the 'create' event.
     */
    _onClick: function() {
        var url;

        if (this.model.get('accessible')) {
            url = this.model.get('reviewRequestURL');

            if (url) {
                window.location = url;
            } else {
                this.model.trigger('create', this.model);
            }
        }
    },

    /*
     * Toggle a progress indicator on for this commit.
     */
    showProgress: function() {
        this.$('.progress').show();
    },

    /*
     * Toggle a progress indicator off for this commit.
     */
    cancelProgress: function() {
        this.$('.progress').hide();
    }
}, {
    strings: {
        COMMIT_NOT_ACCESSIBLE: gettext('(not accessible on this repository)')
    }
});
