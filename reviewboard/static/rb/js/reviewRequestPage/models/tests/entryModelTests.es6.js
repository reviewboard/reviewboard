suite('rb/reviewRequestPage/models/Entry', function() {
    it('parse', function() {
        const reviewRequestEditor = new RB.ReviewRequestEditor({
            reviewRequest: new RB.ReviewRequest(),
        });

        const entry = new RB.ReviewRequestPage.Entry({
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
