/**
 * A view for selecting pages.
 */
RB.PaginationView = Backbone.View.extend({
    template: _.template(dedent`
        <% if (isPaginated) { %>
         <%- splitText %>
         <% if (hasPrevious) { %>
          <span class="paginate-link" data-page="<%- previousPage %>"><a href="?page=<%- previousPage %><%= extraURLOptions %>" title="<%- previousPageText %>">&lt;</a></span>
         <% } %>
         <% _.each(pageNumbers, function(page) { %>
          <% if (page === currentPage) { %>
           <span class="paginate-current" title="<%- currentPageText %>"><%- page %></span>
          <% } else { %>
           <span class="paginate-link" data-page="<%- page %>"><a href="?page=<%- page %><%= extraURLOptions %>"
               title="<% print(interpolate(pageText, [page])); %>"
               ><%- page %></a></span>
          <% } %>
         <% }); %>
         <% if (hasNext) { %>
          <span class="paginate-link" data-page="<%- nextPage %>"><a href="?page=<%- nextPage %><%= extraURLOptions %>" title="<%- nextPageText %>">&gt;</a></span>
         <% } %>
        <% } %>
    `),

    events: {
        'click .paginate-link': '_onPageClicked',
    },

    /**
     * Initialize the view.
     */
    initialize() {
        this.listenTo(this.model, 'change', this.render);
    },

    /**
     * Render the view.
     *
     * Returns:
     *     RB.PaginationView:
     *     This object, for chaining.
     */
    render() {
        this.$el
            .empty()
            .html(this.template(_.defaults({
                splitText: interpolate(
                    gettext('This diff has been split across %s pages:'),
                    [this.model.get('pages')]),
                previousPageText: gettext('Previous Page'),
                nextPageText: gettext('Next Page'),
                currentPageText: gettext('Current Page'),
                extraURLOptions: this._buildExtraQueryString(),
                pageText: gettext('Page %s'),
            }, this.model.attributes)));

        return this;
    },

    /**
     * Build the extra query string to tack onto any pagination links.
     *
     * This will take the current query string on the page, strip out the
     * ``page=`` part, and return the resulting query string for use in
     * any links.
     *
     * Returns:
     *     string:
     *     The new query string to tack onto an existing URL. This will come
     *     with a leading ``&`` if there's content in the string.
     */
    _buildExtraQueryString() {
        /*
         * Ideally we'd use Djblets.parseQueryString() for most of this, but
         * that doesn't maintain order (and it's perhaps not worth doing so).
         * We need to keep the order so that we generate query strings that
         * can be effectively cached by the browser in a reliable way.
         */
        let queryString = window.location.search || '';
        let parts = [];

        if (queryString.startsWith('?')) {
            queryString = queryString.substr(1);
        }

        if (queryString) {
            parts = queryString.split('&');
            const newParts = [];

            for (let i = 0; i < parts.length; i++) {
                const part = parts[i];

                if (!part.startsWith('page=')) {
                    newParts.push(part);
                }
            }

            if (newParts.length > 0) {
                return '&' + newParts.join('&');
            }
        }

        return '';
    },

    /**
     * Callback for when a page number is clicked.
     *
     * Args:
     *     ev (Event):
     *         The click event.
     */
    _onPageClicked(ev) {
        const page = $(ev.currentTarget).data('page');

        if (page !== undefined) {
            this.trigger('pageSelected', page);

            ev.stopPropagation();
            ev.preventDefault();
        }
    },
});
