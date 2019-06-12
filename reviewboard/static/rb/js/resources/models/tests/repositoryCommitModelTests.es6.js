suite('rb/resources/models/RepositoryCommit', function() {
    let model;

    beforeEach(function() {
        model = new RB.RepositoryCommit();
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                author_name: 'Sneezy',
                date: '2013-06-25T23:31:22Z',
                id: '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817',
                message: "Here's a commit message\n\nWith a description",
                review_request_url: 'http://example.com/r/12/',
            });

            expect(data).not.toBe(undefined);
            expect(data.authorName).toBe('Sneezy');
            expect(data.id).toBe('859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817');
            expect(data.date.getUTCFullYear()).toBe(2013);
            expect(data.date.getUTCDate()).toBe(25);
            expect(data.message)
                .toBe("Here's a commit message\n\nWith a description");
            expect(data.summary).toBe("Here's a commit message");
            expect(data.reviewRequestURL).toBe('http://example.com/r/12/');
        });
    });
});
