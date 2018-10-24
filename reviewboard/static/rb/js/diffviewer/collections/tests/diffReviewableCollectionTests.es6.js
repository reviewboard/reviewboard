suite('rb/diffviewer/collections/DiffReviewableCollection', function() {
    describe('Construction', function() {
        it('Sets reviewRequest', function() {
            const reviewRequest = new RB.ReviewRequest();
            const collection = new RB.DiffReviewableCollection([], {
                reviewRequest: reviewRequest,
            });

            expect(collection.reviewRequest).toBe(reviewRequest);
        });
    });

    describe('watchFiles', function() {
        let collection;
        let files;

        beforeEach(function() {
            collection = new RB.DiffReviewableCollection([], {
                reviewRequest: new RB.ReviewRequest(),
            });
            files = new RB.DiffFileCollection();
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
                new RB.DiffFile({
                    filediff: {
                        id: 300,
                        revision: 1,
                    },
                    index: 1,
                    id: 100,
                }),
                new RB.DiffFile({
                    filediff: {
                        id: 301,
                        revision: 1,
                    },
                    interfilediff: {
                        id: 400,
                        revision: 2,
                    },
                    index: 2,
                    id: 101,
                    commentCounts: [1],
                }),
                new RB.DiffFile({
                    baseFileDiffID: 123,
                    filediff: {
                        id: 302,
                        revision: 2,
                    },
                    forceInterdiff: true,
                    forceInterdiffRevision: 1,
                    index: 3,
                    id: 102,
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
            expect(diffReviewable.get('serializedCommentBlocks')).toEqual([1]);

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
