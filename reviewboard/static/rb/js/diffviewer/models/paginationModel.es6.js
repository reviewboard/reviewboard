/**
 * A model representing pagination.
 *
 * Model Attributes:
 *     currentPage (number):
 *         The number of the current page.
 *
 *     hasNext (boolean):
 *         Whether there's a page after the current page.
 *
 *     hasPrevious (boolean):
 *         Whether there's a page before the current page.
 *
 *     isPaginated (boolean):
 *         Whether there are multiple pages.
 *
 *     nextPage (number):
 *         The number of the page after the current page.
 *
 *     pageNumbers (Array of number):
 *         A list of all the page numbers to display.
 *
 *     pages (number):
 *         The total number of pages.
 *
 *     previousPage (number):
 *         The number of the page before the current page.
 */
RB.Pagination = Backbone.Model.extend({
    /**
     * Return the defaults for the model attributes.
     *
     * Returns:
     *     object:
     *     The defaults for the model.
     */
    defaults() {
        return {
            currentPage: null,
            hasNext: false,
            hasPrevious: false,
            isPaginated: false,
            nextPage: null,
            pageNumbers: [],
            pages: 0,
            previousPage: null,
        };
    },

    /**
     * Parse the data given to us by the server.
     *
     * Args:
     *     rsp (object):
     *         The data received from the server.
     *
     * Returns:
     *     object:
     *     The parsed result.
     */
    parse(rsp) {
        return {
            currentPage: rsp.current_page,
            hasNext: rsp.has_next,
            hasPrevious: rsp.has_previous,
            isPaginated: rsp.is_paginated,
            nextPage: rsp.next_page,
            pageNumbers: rsp.page_numbers,
            pages: rsp.pages,
            previousPage: rsp.previous_page,
        };
    },
});
