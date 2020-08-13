suite('rb/reviewRequestPage/models/StatusUpdatesEntry', function() {
    it('parse', function() {
        const diffCommentsData = [
            ['1', '100'],
            ['2', '100-101'],
        ];
        const reviewRequestEditor = new RB.ReviewRequestEditor({
            reviewRequest: new RB.ReviewRequest({ id: 5 }),
        });

        const entry = new RB.ReviewRequestPage.StatusUpdatesEntry({
            diffCommentsData: diffCommentsData,
            id: '0',
            typeID: 'initial_status_updates',
            addedTimestamp: '2017-08-18T13:40:25Z',
            updatedTimestamp: '2017-08-18T16:20:00Z',
            pendingStatusUpdates: true,
            reviewsData: [
                {
                    id: 123,
                    bodyTop: 'My body top',
                    bodyBottom: 'My body bottom',
                    'public': true,
                    shipIt: false,
                },
            ],
            reviewRequestEditor: reviewRequestEditor,
            ignoredAttr: 'ignored',
        }, {
            parse: true,
        });

        expect(entry.id).toBe('0');
        expect(entry.get('diffCommentsData')).toBe(diffCommentsData);
        expect(entry.get('reviewRequestEditor')).toBe(reviewRequestEditor);
        expect(entry.get('typeID')).toBe('initial_status_updates');
        expect(entry.get('addedTimestamp')).toEqual(
            new Date(Date.UTC(2017, 7, 18, 13, 40, 25)));
        expect(entry.get('updatedTimestamp')).toEqual(
            new Date(Date.UTC(2017, 7, 18, 16, 20, 0)));
        expect(entry.get('pendingStatusUpdates')).toBe(true);
        expect(entry.get('ignoredAttr')).toBe(undefined);
        expect(entry.get('reviewRequestId')).toBe(5);

        const reviews = entry.get('reviews');
        expect(reviews.length).toBe(1);

        const review = reviews[0];
        expect(review.get('id')).toBe(123);
        expect(review.get('bodyTop')).toBe('My body top');
        expect(review.get('bodyBottom')).toBe('My body bottom');
        expect(review.get('public')).toBe(true);
        expect(review.get('shipIt')).toBe(false);
    });
});
