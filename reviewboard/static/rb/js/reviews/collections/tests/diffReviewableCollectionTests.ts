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
    DiffFileCollection,
    DiffReviewableCollection,
} from 'reviewboard/reviews';


suite('rb/diffviewer/collections/DiffReviewableCollection', function() {
    describe('Construction', function() {
        it('Sets reviewRequest', function() {
            const reviewRequest = new ReviewRequest();
            const collection = new DiffReviewableCollection([], {
                reviewRequest: reviewRequest,
            });

            expect(collection.reviewRequest).toBe(reviewRequest);
        });
    });

    describe('watchFiles', function() {
        let collection: DiffReviewableCollection;
        let files: DiffFileCollection;

        beforeEach(function() {
            collection = new DiffReviewableCollection([], {
                reviewRequest: new ReviewRequest(),
            });
            files = new DiffFileCollection();
        });

        it('Initially populates', function() {
            spyOn(collection, '_populateFromFiles');

            collection.watchFiles(files);

            expect(collection._populateFromFiles).toHaveBeenCalled();
        });

        it('Populates on files.reset', function() {
            spyOn(collection, 'trigger');
            spyOn(collection, 'reset');

            collection.watchFiles(files);

            files.reset([
                new DiffFile({
                    filediff: {
                        id: 300,
                        revision: 1,
                    },
                    id: 100,
                    index: 1,
                }),
                new DiffFile({
                    filediff: {
                        id: 301,
                        revision: 1,
                    },
                    id: 101,
                    index: 2,
                    interfilediff: {
                        id: 400,
                        revision: 2,
                    },
                    serializedCommentBlocks: {
                        '2-2': [
                            {
                                comment_id: 1,
                                issue_opened: false,
                                line: 2,
                                localdraft: false,
                                num_lines: 2,
                                review_id: 1,
                                text: 'Comment',
                                user: { name: 'testuser' },
                            },
                        ],
                    },
                }),
                new DiffFile({
                    baseFileDiffID: 123,
                    filediff: {
                        id: 302,
                        revision: 2,
                    },
                    forceInterdiff: true,
                    forceInterdiffRevision: 1,
                    id: 102,
                    index: 3,
                }),
            ]);

            expect(collection.reset).toHaveBeenCalled();
            expect(collection.trigger).toHaveBeenCalledWith('populating');
            expect(collection.trigger).toHaveBeenCalledWith('populated');
            expect(collection.length).toBe(3);

            let diffReviewable = collection.at(0);
            expect(diffReviewable.get('baseFileDiffID')).toBe(null);
            expect(diffReviewable.get('file').id).toBe(100);
            expect(diffReviewable.get('reviewRequest'))
                .toBe(collection.reviewRequest);
            expect(diffReviewable.get('fileDiffID')).toBe(300);
            expect(diffReviewable.get('interFileDiffID')).toBe(null);
            expect(diffReviewable.get('revision')).toBe(1);
            expect(diffReviewable.get('interdiffRevision')).toBe(null);

            diffReviewable = collection.at(1);
            expect(diffReviewable.get('baseFileDiffID')).toBe(null);
            expect(diffReviewable.get('file').id).toBe(101);
            expect(diffReviewable.get('reviewRequest'))
                .toBe(collection.reviewRequest);
            expect(diffReviewable.get('fileDiffID')).toBe(301);
            expect(diffReviewable.get('interFileDiffID')).toBe(400);
            expect(diffReviewable.get('revision')).toBe(1);
            expect(diffReviewable.get('interdiffRevision')).toBe(2);
            expect(diffReviewable.get('serializedCommentBlocks')).toEqual(
                {
                    '2-2': [
                        {
                            comment_id: 1,
                            issue_opened: false,
                            line: 2,
                            localdraft: false,
                            num_lines: 2,
                            review_id: 1,
                            text: 'Comment',
                            user: { name: 'testuser' },
                        },
                    ],
                });

            diffReviewable = collection.at(2);
            expect(diffReviewable.get('baseFileDiffID')).toBe(123);
            expect(diffReviewable.get('file').id).toBe(102);
            expect(diffReviewable.get('reviewRequest'))
                .toBe(collection.reviewRequest);
            expect(diffReviewable.get('fileDiffID')).toBe(302);
            expect(diffReviewable.get('interFileDiffID')).toBe(null);
            expect(diffReviewable.get('revision')).toBe(2);
            expect(diffReviewable.get('interdiffRevision')).toBe(1);
        });
    });
});
