suite('rb/reviewRequestPage/models/ReviewEntry', function() {
    it('parse', function() {
        const diffCommentsData = [
            ['1', '100'],
            ['2', '100-101'],
        ];
        const reviewRequestEditor = new RB.ReviewRequestEditor({
            reviewRequest: new RB.ReviewRequest(),
        });

        const entry = new RB.ReviewRequestPage.ReviewEntry({
            diffCommentsData: diffCommentsData,
            id: '100',
            typeID: 'review',
            addedTimestamp: '2017-08-18T13:40:25Z',
            updatedTimestamp: '2017-08-18T16:20:00Z',
            reviewData: {
                id: 123,
                bodyTop: 'My body top',
                bodyBottom: 'My body bottom',
                'public': true,
                shipIt: false,
            },
            reviewRequestEditor: reviewRequestEditor,
            ignoredAttr: 'ignored',
        }, {
            parse: true,
        });

        expect(entry.id).toBe('100');
        expect(entry.get('diffCommentsData')).toBe(diffCommentsData);
        expect(entry.get('reviewRequestEditor')).toBe(reviewRequestEditor);
        expect(entry.get('typeID')).toBe('review');
        expect(entry.get('addedTimestamp')).toEqual(
            new Date(Date.UTC(2017, 7, 18, 13, 40, 25)));
        expect(entry.get('updatedTimestamp')).toEqual(
            new Date(Date.UTC(2017, 7, 18, 16, 20, 0)));
        expect(entry.get('ignoredAttr')).toBe(undefined);

        const review = entry.get('review');
        expect(review).toBeTruthy();
        expect(review.get('id')).toBe(123);
        expect(review.get('bodyTop')).toBe('My body top');
        expect(review.get('bodyBottom')).toBe('My body bottom');
        expect(review.get('public')).toBe(true);
        expect(review.get('shipIt')).toBe(false);
    });
});
