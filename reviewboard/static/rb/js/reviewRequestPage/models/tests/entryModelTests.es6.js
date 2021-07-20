suite('rb/reviewRequestPage/models/Entry', function() {
    let reviewRequestEditor;
    let entry;

    beforeEach(function() {
        reviewRequestEditor = new RB.ReviewRequestEditor({
            reviewRequest: new RB.ReviewRequest(),
        });

        entry = new RB.ReviewRequestPage.Entry({
            reviewRequestEditor: reviewRequestEditor,
            id: '123',
            typeID: 'some_type',
            addedTimestamp: '2017-08-18T13:40:25Z',
            updatedTimestamp: '2017-08-18T16:20:00Z',
            ignoredAttr: 'ignored',
        }, {
            parse: true,
        });
    });

    it('parse', function() {
        expect(entry.id).toBe('123');
        expect(entry.get('reviewRequestEditor')).toBe(reviewRequestEditor);
        expect(entry.get('addedTimestamp'))
            .toEqual(new Date(Date.UTC(2017, 7, 18, 13, 40, 25)));
        expect(entry.get('updatedTimestamp'))
            .toEqual(new Date(Date.UTC(2017, 7, 18, 16, 20, 0)));
        expect(entry.get('typeID')).toBe('some_type');
    });

    describe('isUpdated', function() {
        it('With newer updateTimestamp only', function() {
            const metadata = {
                updatedTimestamp: '2017-08-20T23:10:12Z',
            };

            expect(entry.isUpdated(metadata)).toBe(true);
        });

        it('With older updateTimestamp only', function() {
            const metadata = {
                updatedTimestamp: '2017-08-18T12:10:12Z',
            };

            expect(entry.isUpdated(metadata)).toBe(false);
        });

        it('With changed etag', function() {
            const metadata = {
                etag: 'new-etag',
                updatedTimestamp: '2017-08-18T16:20:00Z',
            };

            expect(entry.isUpdated(metadata)).toBe(true);
        });

        it('With same updateTimestamp and etag', function() {
            entry.set('etag', 'old-etag');

            const metadata = {
                etag: 'old-etag',
                updatedTimestamp: '2017-08-18T16:20:00Z',
            };

            expect(entry.isUpdated(metadata)).toBe(false);
        });
    });
});
