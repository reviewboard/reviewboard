import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import {
    type Review,
    ReviewRequest,
} from 'reviewboard/common';
import { DiffCommentBlock } from 'reviewboard/reviews';


suite('rb/diffviewer/models/DiffCommentBlock', function() {
    let reviewRequest: ReviewRequest;
    let review: Review;

    beforeEach(function() {
        reviewRequest = new ReviewRequest({
            reviewURL: '/r/1/',
        });
        review = reviewRequest.createReview();
    });

    describe('createComment', function() {
        it('With a rendered view', function() {
            const commentBlock = new DiffCommentBlock({
                beginLineNum: 4,
                endLineNum: 5,
                fileDiffID: 3,
                renderVersion: 2,
                review: review,
                reviewRequest: reviewRequest,
                viewMode: 'rendered',
            });

            const extraData = commentBlock.get('draftComment')
                .get('extraData');
            expect(extraData.viewMode).toBe('rendered');
            expect(extraData.renderVersion).toBe(2);
        });

        it('Without a rendered view', function() {
            const commentBlock = new DiffCommentBlock({
                beginLineNum: 4,
                endLineNum: 5,
                fileDiffID: 3,
                review: review,
                reviewRequest: reviewRequest,
            });

            const extraData = commentBlock.get('draftComment')
                .get('extraData');
            expect(extraData.viewMode).toBe(undefined);
            expect(extraData.renderVersion).toBe(undefined);
        });
    });
});
