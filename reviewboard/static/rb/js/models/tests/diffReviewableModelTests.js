describe('models/DiffReviewable', function() {
    var callbacks;

    beforeEach(function() {
        callbacks = {
            success: function() {},
            error: function() {},
            complete: function() {}
        };

        spyOn(callbacks, 'success');
        spyOn(callbacks, 'error');
        spyOn(callbacks, 'complete');
    });

    describe('getRenderedDiff', function() {
        it('Without interdiffs', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequestURL: '/r/1/',
                revision: 2
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/?index=4&' + AJAX_SERIAL);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiff({
                fileDiffID: 3,
                fileIndex: 4
            }, callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('With interdiffs', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequestURL: '/r/1/',
                revision: 2,
                interdiffRevision: 3
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2-3/fragment/3/?index=4&' + AJAX_SERIAL);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiff({
                fileDiffID: 3,
                fileIndex: 4
            }, callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('Overriding options', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequestURL: '/r/1/',
                revision: 2,
                interdiffRevision: 3
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/11/diff/12-13/fragment/3/?index=4&' + AJAX_SERIAL);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiff({
                reviewRequestURL: '/r/11/',
                revision: 12,
                interdiffRevision: 13,
                fileDiffID: 3,
                fileIndex: 4
            }, callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });
    });

    describe('getRenderedDiffFragment', function() {
        it('Without interdiffs', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequestURL: '/r/1/',
                revision: 2
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe('/r/1/diff/2/fragment/3/chunk/4/');
                expect(request.data.index).toBe(5);
                expect(request.data['lines-of-context']).toBe(6);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiffFragment({
                fileDiffID: 3,
                chunkIndex: 4,
                fileIndex: 5,
                linesOfContext: 6
            }, callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('With interdiffs', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequestURL: '/r/1/',
                revision: 2,
                interdiffRevision: 3
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe('/r/1/diff/2-3/fragment/3/chunk/4/');
                expect(request.data.index).toBe(5);
                expect(request.data['lines-of-context']).toBe(6);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiffFragment({
                fileDiffID: 3,
                chunkIndex: 4,
                fileIndex: 5,
                linesOfContext: 6
            }, callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('Overriding options', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequestURL: '/r/1/',
                revision: 2,
                interdiffRevision: 3
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe('/r/11/diff/12-13/fragment/3/chunk/4/');
                expect(request.data.index).toBe(5);
                expect(request.data['lines-of-context']).toBe(6);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiffFragment({
                reviewRequestURL: '/r/11/',
                revision: 12,
                interdiffRevision: 13,
                fileDiffID: 3,
                chunkIndex: 4,
                fileIndex: 5,
                linesOfContext: 6
            }, callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });
    });
});
