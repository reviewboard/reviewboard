suite('rb/resources/collections/RepositoryCommits', function() {
    var collection,
        url = '/api/repositories/123/commits/',
        start = '859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817';

    beforeEach(function() {
        collection = new RB.RepositoryCommits([], {
            urlBase: url,
            start: start
        });
    });

    describe('Methods', function() {
        it('fetch', function() {
            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.url)
                    .toBe(url + '?start=' + start);
                expect(request.type).toBe('GET');

                request.success({
                    stat: 'ok',
                    commits: [
                        {
                            author_name: "Christian Hammond",
                            date: "2013-06-25T23:31:22Z",
                            id: "859d4e148ce3ce60bbda6622cdbe5c2c2f8d9817",
                            message: "Merge branch 'release-1.7.x'",
                            parent: "84c730c7823b653a5bbcc007188d5c85a7c4ac58",
                            review_request_url: ""
                        },
                        {
                            author_name: "Christian Hammond",
                            date: "2013-06-25T23:30:59Z",
                            id: "92463764015ef463b4b6d1a1825fee7aeec8cb15",
                            message: "Fixed the bug number for the " +
                                     "blacktriangledown bug.",
                            parent: "f5a35f1d8a8dcefb336a8e3211334f1f50ea7792",
                            review_request_url: "http://example.com/r/18274/"
                        },
                        {
                            author_name: "Christian Hammond",
                            date: "2013-06-25T22:53:32Z",
                            id: "84c730c7823b653a5bbcc007188d5c85a7c4ac58",
                            message: [
                                "Don't expose child resources in ",
                                "ValidateDiffResource.\n\nFor convenience, ",
                                "ValidateDiffResource inherited from ",
                                "DiffResource.\nThis brought along the child ",
                                "resources, which weren't valid to have.\n",
                                "That ended up breaking docs, which tried ",
                                "to traverse them."].join(''),
                            parent: "4150004c2f332747d92769d8133571dfac8c2803",
                            review_request_url: ""
                        }
                    ]
                });

            });

            collection.fetch();

            expect($.ajax).toHaveBeenCalled();
            expect(collection.length).toBe(3);
            expect(collection.at(0).get('authorName'))
                .toBe('Christian Hammond');
            expect(collection.at(1).get('date').getUTCHours()).toBe(23);
            expect(collection.at(2).get('summary'))
                .toBe("Don't expose child resources in ValidateDiffResource.");
            expect(collection.at(1).get('reviewRequestURL'))
                .toBe('http://example.com/r/18274/');
        });

        it('url', function() {
            expect(_.result(collection, 'url'))
                .toBe(url + '?start=' + start);
        });
    });
});
