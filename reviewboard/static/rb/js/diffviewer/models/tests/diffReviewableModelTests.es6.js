suite('rb/diffviewer/models/DiffReviewable', function() {
    let reviewRequest;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            reviewURL: '/r/1/',
        });
    });

    describe('getRenderedDiff', function() {
        it('Without interdiffs', async function() {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                revision: 2,
                file: new RB.DiffFile({
                    index: 4,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/?index=4&_=' + TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiff();
            expect($.ajax).toHaveBeenCalled();
            expect(html).toEqual('abc');
        });

        it('With callbacks', function(done) {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                revision: 2,
                file: new RB.DiffFile({
                    index: 4,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/?index=4&show-deleted=1&_=' +
                    TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });
            spyOn(console, 'warn');

            diffReviewable.getRenderedDiff(
                {
                    success: html => {
                        expect($.ajax).toHaveBeenCalled();
                        expect(html).toEqual('abc');
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                    error: () => done.fail(),
                },
                undefined,
                {
                    showDeleted: true,
                });
        });

        it('With interdiffs', async function() {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                revision: 2,
                interdiffRevision: 3,
                file: new RB.DiffFile({
                    index: 4,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2-3/fragment/3/?index=4&_=' + TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiff();
            expect($.ajax).toHaveBeenCalled();
            expect(html).toEqual('abc');
        });

        it('With base FileDiff', async function() {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                revision: 2,
                baseFileDiffID: 1,
                file: new RB.DiffFile({
                    index: 4,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/?base-filediff-id=1&index=4&_=' +
                    TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiff();
            expect(html).toEqual('abc');
        });
    });

    describe('getRenderedDiffFragment', function() {
        it('Without interdiffs', async function() {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                revision: 2,
                file: new RB.DiffFile({
                    index: 5,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/chunk/4/?index=5&' +
                    'lines-of-context=6&_=' + TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiffFragment({
                chunkIndex: 4,
                linesOfContext: 6,
            });

            expect($.ajax).toHaveBeenCalled();
            expect(html).toEqual('abc');
        });

        it('Without interdiffs', function(done) {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                revision: 2,
                file: new RB.DiffFile({
                    index: 5,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/chunk/4/?index=5&' +
                    'lines-of-context=6&_=' + TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });
            spyOn(console, 'warn');

            diffReviewable.getRenderedDiffFragment({
                chunkIndex: 4,
                linesOfContext: 6,
                success: html => {
                    expect($.ajax).toHaveBeenCalled();
                    expect(html).toEqual('abc');
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
                error: () => done.fail(),
            });
        });

        it('With interdiffs', async function() {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                revision: 2,
                interdiffRevision: 3,
                interFileDiffID: 4,
                file: new RB.DiffFile({
                    index: 5,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2-3/fragment/3-4/chunk/4/?index=5&' +
                    'lines-of-context=6&_=' + TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiffFragment({
                chunkIndex: 4,
                linesOfContext: 6,
            });

            expect($.ajax).toHaveBeenCalled();
            expect(html).toEqual('abc');
        });

        it('With base filediff ID', async function() {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                baseFileDiffID: 123,
                fileDiffID: 3,
                revision: 2,
                interdiffRevision: 3,
                interFileDiffID: 4,
                file: new RB.DiffFile({
                    index: 5,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2-3/fragment/3-4/chunk/4/' +
                    '?base-filediff-id=123&index=5&' +
                    'lines-of-context=6&_=' + TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiffFragment({
                chunkIndex: 4,
                linesOfContext: 6,
            });

            expect($.ajax).toHaveBeenCalled();
            expect(html).toEqual('abc');
        });

        it('With callbacks', function(done) {
            const diffReviewable = new RB.DiffReviewable({
                reviewRequest: reviewRequest,
                fileDiffID: 3,
                revision: 2,
                file: new RB.DiffFile({
                    index: 5,
                }),
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/chunk/4/?index=5&' +
                    'lines-of-context=6&_=' + TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });
            spyOn(console, 'warn');

            diffReviewable.getRenderedDiffFragment(
                {
                    success: html => {
                        expect($.ajax).toHaveBeenCalled();
                        expect(html).toEqual('abc');
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                    error: () => done.fail(),
                },
                undefined,
                {
                    chunkIndex: 4,
                    linesOfContext: 6,
                });
        });
    });
});
