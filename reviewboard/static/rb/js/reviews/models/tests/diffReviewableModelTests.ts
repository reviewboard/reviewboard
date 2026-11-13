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

import { type SerializedDiffComment } from '../commentData';


suite('rb/diffviewer/models/DiffReviewable', function() {
    let reviewRequest: ReviewRequest;

    beforeEach(function() {
        reviewRequest = new ReviewRequest({
            reviewURL: '/r/1/',
        });
    });

    describe('loadSerializedCommentBlock', function() {
        const baseComment: SerializedDiffComment = {
            comment_id: 1,
            html: 'Comment',
            issue_opened: false,
            issue_status: '',
            line: 4,
            localdraft: false,
            num_lines: 2,
            review_id: 1,
            review_request_id: 1,
            rich_text: false,
            text: 'Comment',
            url: '',
            user: {
                name: 'testuser',
                username: 'testuser',
            },
            viewMode: 'source',
        };

        it('With view mode data', function() {
            const diffReviewable = new DiffReviewable({
                fileDiffID: 3,
                renderVersion: 2,
                reviewRequest: reviewRequest,
                revision: 2,
            });

            const comment: SerializedDiffComment = {
                ...baseComment,
                renderVersion: 2,
                viewMode: 'rendered',
            };

            diffReviewable.loadSerializedCommentBlock([comment]);

            const commentBlock = diffReviewable.commentBlocks.at(0);
            expect(commentBlock.get('beginLineNum')).toBe(4);
            expect(commentBlock.get('endLineNum')).toBe(5);
            expect(commentBlock.get('viewMode')).toBe('rendered');
            expect(commentBlock.get('renderVersion')).toBe(2);
        });

        it('Without view mode data', function() {
            const diffReviewable = new DiffReviewable({
                fileDiffID: 3,
                reviewRequest: reviewRequest,
                revision: 2,
            });

            /* Simulate data from before view modes were stored. */
            const comment: Partial<SerializedDiffComment> = {...baseComment};
            delete comment.viewMode;

            diffReviewable.loadSerializedCommentBlock([
                comment as SerializedDiffComment,
            ]);

            const commentBlock = diffReviewable.commentBlocks.at(0);
            expect(commentBlock.get('viewMode')).toBe('source');
            expect(commentBlock.get('renderVersion')).toBe(undefined);
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

        it('With viewMode=rendered', async function() {
            const diffReviewable = new DiffReviewable({
                file: new DiffFile({
                    index: 4,
                }),
                fileDiffID: 3,
                reviewRequest: reviewRequest,
                revision: 2,
                viewMode: 'rendered',
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/?index=4&view-mode=rendered&_=' +
                    TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiff();
            expect(html).toEqual('abc');
        });
    });

    describe('getRenderedDiffFragment', function() {
        it('With viewMode=rendered', async function() {
            const diffReviewable = new DiffReviewable({
                file: new DiffFile({
                    index: 5,
                }),
                fileDiffID: 3,
                reviewRequest: reviewRequest,
                revision: 2,
                viewMode: 'rendered',
            });

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('GET');
                expect(request.url).toBe(
                    '/r/1/diff/2/fragment/3/chunk/4/?index=5&' +
                    'view-mode=rendered&_=' + TEMPLATE_SERIAL);

                request.complete({ responseText: 'abc' });
            });

            const html = await diffReviewable.getRenderedDiffFragment({
                chunkIndex: 4,
            });

            expect(html).toEqual('abc');
        });

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
