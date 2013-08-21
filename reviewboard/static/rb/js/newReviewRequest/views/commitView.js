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
        '  <% if (reviewRequestURL) { %>',
        '   <div class="rb-icon rb-icon-jump-to jump-to-commit"/>',
        '  <% } %>',
        '</div>',
        '<div>',
        ' by <span class="author"><%- authorName %></span>, ',
        ' <time class="timesince" datetime="<%- date.toISOString() %>"></time>',
        '</div>'
    ].join('')),

    events: {
        'click': '_onClick'
    },

    /*
     * Render the view.
     */
    render: function() {
        this.$el.html(this.template(this.model.attributes));
        this.$('.timesince').timesince();

        return this;
    },

    /*
     * Handler for when the commit is clicked.
     *
     * If a review request already exists for this commit, redirect the browser
     * to it. If not, trigger the 'create' event.
     */
    _onClick: function() {
        var url = this.model.get('reviewRequestURL');

        if (url) {
            window.location = url;
        } else {
            this.model.trigger('create', this.model);
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
