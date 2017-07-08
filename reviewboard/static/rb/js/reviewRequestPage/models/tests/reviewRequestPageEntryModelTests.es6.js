suite('rb/reviewRequestPage/models/ReviewRequestPageEntry', function() {
    it('parse', function() {
        const reviewRequestEditor = new RB.ReviewRequestEditor({
            reviewRequest: new RB.ReviewRequest(),
        });

        const entry = new RB.ReviewRequestPageEntry({
            reviewRequestEditor: reviewRequestEditor,
            ignoredAttr: 'ignored',
        }, {
            parse: true,
        });

        expect(entry.attributes).toEqual({
            reviewRequestEditor: reviewRequestEditor,
        });
    });
});
