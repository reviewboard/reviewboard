suite('rb/diffviewer/models/Pagination', function() {
    var model;

    beforeEach(function() {
        model = new RB.Pagination();
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                is_paginated: true,
                pages: 4,
                has_previous: true,
                has_next: true,
                page_numbers: [1, 2, 3, 4],
                previous_page: 1,
                next_page: 3,
                current_page: 2
            });

            expect(data).not.toBe(undefined);
            expect(data.isPaginated).toBe(true);
            expect(data.pages).toBe(4);
            expect(data.pageNumbers).toEqual([1, 2, 3, 4]);
            expect(data.hasPrevious).toBe(true);
            expect(data.hasNext).toBe(true);
            expect(data.previousPage).toBe(1);
            expect(data.nextPage).toBe(3);
            expect(data.currentPage).toBe(2);
        });
    });
});
