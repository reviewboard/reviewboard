suite('rb/reviewRequestPage/models/Entry', function() {
    it('parse', function() {
        const reviewRequestEditor = new RB.ReviewRequestEditor({
            reviewRequest: new RB.ReviewRequest(),
        });

        const entry = new RB.ReviewRequestPage.Entry({
            reviewRequestEditor: reviewRequestEditor,
            id: '123',
            typeID: 'some_type',
            timestamp: '2017-08-18T13:40:25Z',
            ignoredAttr: 'ignored',
        }, {
            parse: true,
        });

        expect(entry.id).toBe('123');
        expect(entry.get('reviewRequestEditor')).toBe(reviewRequestEditor);
        expect(entry.get('timestamp'))
            .toEqual(new Date(Date.UTC(2017, 7, 18, 13, 40, 25)));
        expect(entry.get('typeID')).toBe('some_type');
    });
});
