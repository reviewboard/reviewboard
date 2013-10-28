/*
 * A view for selecting pages.
 */
RB.PaginationView = Backbone.View.extend({
    template: _.template([
        '<% if (isPaginated) { %>',
        ' <%- splitText %>',
        ' <% if (hasPrevious) { %>',
        '  <span class="paginate-link" data-page="<%- previousPage %>"><a href="?page=<%- previousPage %>" title="<%- previousPageText %>">&lt;</a></span>',
        ' <% } %>',
        ' <% _.each(pageNumbers, function(page) { %>',
        '  <% if (page === currentPage) { %>',
        '   <span class="paginate-current" title="<%- currentPageText %>"><%- page %></span>',
        '  <% } else { %>',
        '   <span class="paginate-link" data-page="<%- page %>"><a href="?page=<%- page %>"',
        '       title="<% print(interpolate(pageText, [page])); %>"',
        '       ><%- page %></a></span>',
        '  <% } %>',
        ' <% }); %>',
        ' <% if (hasNext) { %>',
        '  <span class="paginate-link" data-page="<%- nextPage %>"><a href="?page=<%- nextPage %>" title="<%- nextPageText %>">&gt;</a></span>',
        ' <% } %>',
        '<% } %>'
    ].join('')),

    events: {
        'click .paginate-link': '_onPageClicked'
    },

    /*
     * Initialize the view.
     */
    initialize: function() {
        this.listenTo(this.model, 'change', this.render);
    },

    /*
     * Render the view.
     */
    render: function() {
        this.$el
            .empty()
            .html(this.template(_.defaults({
                splitText: interpolate(
                    gettext('This diff has been split across %s pages:'),
                    [this.model.get('pages')]),
                previousPageText: gettext('Previous Page'),
                nextPageText: gettext('Next Page'),
                currentPageText: gettext('Current Page'),
                pageText: gettext('Page %s')
            }, this.model.attributes)));

        return this;
    },

    _onPageClicked: function(ev) {
        var page = $(ev.currentTarget).data('page');

        if (page !== undefined) {
            this.trigger('pageSelected', page);
            return false;
        }
    }
});
