suite('rb/diffviewer/models/DiffReviewable', function() {
    var callbacks,
        reviewRequest;

    beforeEach(function() {
        callbacks = {
            success: function() {},
            error: function() {},
            complete: function() {}
        };

        reviewRequest = new RB.ReviewRequest({
            reviewURL: '/r/1/'
        });

        spyOn(callbacks, 'success');
        spyOn(callbacks, 'error');
        spyOn(callbacks, 'complete');
    });

    describe('getRenderedDiff', function() {
        it('Without interdiffs', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                fileIndex: 4,
                revision: 2
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/?index=4&' + TEMPLATE_SERIAL);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiff(callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('With interdiffs', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                fileIndex: 4,
                revision: 2,
                interdiffRevision: 3
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2-3/fragment/3/?index=4&' + TEMPLATE_SERIAL);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiff(callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });
    });

    describe('getRenderedDiffFragment', function() {
        it('Without interdiffs', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                fileIndex: 5,
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
                chunkIndex: 4,
                linesOfContext: 6
            }, callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('With interdiffs', function() {
            var diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                fileIndex: 5,
                revision: 2,
                interdiffRevision: 3,
                interFileDiffID: 4
            });

            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('GET');
                expect(request.url).toBe('/r/1/diff/2-3/fragment/3-4/chunk/4/');
                expect(request.data.index).toBe(5);
                expect(request.data['lines-of-context']).toBe(6);

                request.success('abc');
                request.complete('abc', 'success');
            });

            diffReviewable.getRenderedDiffFragment({
                chunkIndex: 4,
                linesOfContext: 6
            }, callbacks);

            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalledWith('abc');
            expect(callbacks.complete).toHaveBeenCalledWith('abc', 'success');
            expect(callbacks.error).not.toHaveBeenCalled();
        });
    });
});
