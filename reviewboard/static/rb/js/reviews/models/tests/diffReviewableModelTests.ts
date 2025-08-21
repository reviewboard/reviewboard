import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import { ReviewRequest } from 'reviewboard/common';
import {
    DiffFile,
    DiffReviewable,
} from 'reviewboard/reviews';


suite('rb/diffviewer/models/DiffReviewable', function() {
    let reviewRequest: ReviewRequest;

    beforeEach(function() {
        reviewRequest = new ReviewRequest({
            reviewURL: '/r/1/',
        });
    });

    describe('getRenderedDiff', function() {
        it('Without interdiffs', async function() {
            const diffReviewable = new DiffReviewable({
                file: new DiffFile({
                    index: 4,
                }),
                fileDiffID: 3,
                reviewRequest: reviewRequest,
                revision: 2,
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

        it('With interdiffs', async function() {
            const diffReviewable = new DiffReviewable({
                file: new DiffFile({
                    index: 4,
                }),
                fileDiffID: 3,
                interdiffRevision: 3,
                reviewRequest: reviewRequest,
                revision: 2,
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
            const diffReviewable = new DiffReviewable({
                baseFileDiffID: 1,
                file: new DiffFile({
                    index: 4,
                }),
                fileDiffID: 3,
                reviewRequest: reviewRequest,
                revision: 2,
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
            const diffReviewable = new DiffReviewable({
                file: new DiffFile({
                    index: 5,
                }),
                fileDiffID: 3,
                reviewRequest: reviewRequest,
                revision: 2,
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

        it('With interdiffs', async function() {
            const diffReviewable = new DiffReviewable({
                file: new DiffFile({
                    index: 5,
                }),
                fileDiffID: 3,
                interFileDiffID: 4,
                interdiffRevision: 3,
                reviewRequest: reviewRequest,
                revision: 2,
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
            const diffReviewable = new DiffReviewable({
                baseFileDiffID: 123,
                file: new DiffFile({
                    index: 5,
                }),
                fileDiffID: 3,
                interFileDiffID: 4,
                interdiffRevision: 3,
                reviewRequest: reviewRequest,
                revision: 2,
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

        it('With skipStaticMedia=true', async () => {
            const diffReviewable = new DiffReviewable({
                file: new DiffFile({
                    index: 4,
                }),
                fileDiffID: 3,
                reviewRequest: reviewRequest,
                revision: 2,
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/?index=4&' +
                    'skip-static-media=1&_=' +
                    TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiff({
                skipStaticMedia: true,
            });
            expect($.ajax).toHaveBeenCalled();
            expect(html).toEqual('abc');
        });
    });
});
