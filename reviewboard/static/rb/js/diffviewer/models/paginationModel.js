/*
 * A model representing pagination.
 */
RB.Pagination = Backbone.Model.extend({
    defaults: {
        isPaginated: false,
        pages: 0,
        hasPrevious: false,
        hasNext: false,
        pageNumbers: [],
        previousPage: null,
        nextPage: null,
        currentPage: null
    },

    /*
     * Parse the data given to us by the server.
     */
    parse: function(rsp) {
        return {
            isPaginated: rsp.is_paginated,
            pages: rsp.pages,
            hasPrevious: rsp.has_previous,
            hasNext: rsp.has_next,
            pageNumbers: rsp.page_numbers,
            previousPage: rsp.previous_page,
            nextPage: rsp.next_page,
            currentPage: rsp.current_page
        };
    }
});
