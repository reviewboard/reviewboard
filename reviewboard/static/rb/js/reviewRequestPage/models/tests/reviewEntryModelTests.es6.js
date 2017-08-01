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

        expect(entry.get('diffCommentsData')).toBe(diffCommentsData);
        expect(entry.get('reviewRequestEditor')).toBe(reviewRequestEditor);
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
