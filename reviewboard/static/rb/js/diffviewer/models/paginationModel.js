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
    }
});
