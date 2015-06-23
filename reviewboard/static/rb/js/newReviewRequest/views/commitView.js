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
        '<div class="progress"></div>',
        '<div class="summary">',
        ' <%- summary %>',
        '  <% if (accessible && reviewRequestURL) { %>',
        '   <div class="rb-icon rb-icon-jump-to jump-to-commit"/>',
        '  <% } %>',
        '</div>',
        '<div><%= details %></div>'
    ].join('')),

    events: {
        'click': '_onClick'
    },

    /*
     * Render the view.
     */
    render: function() {
        var commitID = this.model.get('id'),
            date = this.model.get('date'),
            details;

        if (this.model.get('accessible')) {
            details = interpolate(
                date ? gettext('Revision %(revision)s by <span class="author">%(author)s</span>, <time class="timesince" datetime="%(date)s"></time>.')
                     : gettext('Revision %(revision)s by <span class="author">%(author)s</span>.'),
                {
                    revision: _.escape(commitID),
                    author: _.escape(this.model.get('authorName') ||
                                     gettext('<unknown>')),
                    date: date ? date.toISOString() : null
                },
                true)
        } else {
            details = interpolate(
                gettext('Revision %(revision)s (not accessible on this repository)'),
                {
                    revision: _.escape(commitID)
                },
                true);
            this.$el.addClass('disabled');
        }

        if (commitID.length === 40) {
            commitID = commitID.slice(0, 7);
        }

        this.$el.html(this.template(_.defaults({
            details: details
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
});
