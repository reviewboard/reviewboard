suite('rb/resources/collections/ResourceCollection', function() {
    let collection;
    let reviewRequest;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            id: 123,
            loaded: true,
            links: {
                reviews: {
                    href: '/api/review-requests/123/reviews/',
                },
            },
        });

        spyOn(reviewRequest, 'ready').and.callFake(
            (options, context) => options.ready.call(context));

        collection = new RB.ResourceCollection([], {
            model: RB.Review,
            parentResource: reviewRequest,
        });
    });

    describe('Methods', function() {
        describe('fetch', function() {
            it('Populates collection', function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/');
                    expect(request.type).toBe('GET');

                    request.success({
                        stat: 'ok',
                        total_results: 2,
                        links: {
                            self: {
                                method: 'GET',
                                href: '/api/review-requests/123/reviews/',
                            },
                            next: {
                                method: 'GET',
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=25',
                            },
                        },
                        reviews: [
                            {
                                id: 1,
                                links: {},
                            },
                            {
                                id: 2,
                                links: {},
                            },
                        ],
                    });
                });

                collection.fetch();

                expect($.ajax).toHaveBeenCalled();
                expect(collection.length).toBe(2);
                expect(collection.at(0).id).toBe(1);
                expect(collection.at(1).id).toBe(2);
                expect(collection.hasPrev).toBe(false);
                expect(collection.hasNext).toBe(true);
            });

            it('With start=', function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/');
                    expect(request.data).not.toBe(undefined);
                    expect(request.data.start).toBe(100);
                });

                collection.fetch({
                    start: 100,
                });

                expect($.ajax).toHaveBeenCalled();
            });

            describe('With parentResource', function() {
                it('Calls parentResource.ready', function() {
                    spyOn(RB.BaseCollection.prototype, 'fetch');

                    collection.fetch();

                    expect(reviewRequest.ready).toHaveBeenCalled();
                    expect(RB.BaseCollection.prototype.fetch)
                        .toHaveBeenCalled();
                });
            });
        });

        describe('fetchAll', function() {
            it('Spanning pages', function() {
                let numFetches = 0;

                spyOn($, 'ajax').and.callFake(request => {
                    console.assert(numFetches < 2);

                    expect(request.type).toBe('GET');

                    numFetches++;

                    if (numFetches === 1) {
                        expect(request.url).toBe(
                            '/api/review-requests/123/reviews/');

                        request.success({
                            stat: 'ok',
                            total_results: 4,
                            links: {
                                self: {
                                    method: 'GET',
                                    href: '/api/review-requests/123/reviews/',
                                },
                                next: {
                                    method: 'GET',
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=25',
                                },
                            },
                            reviews: [
                                {
                                    id: 1,
                                    links: {},
                                },
                                {
                                    id: 2,
                                    links: {},
                                },
                            ],
                        });
                    } else if (numFetches === 2) {
                        expect(request.url).toBe(
                            '/api/review-requests/123/reviews/?start=25');

                        request.success({
                            stat: 'ok',
                            total_results: 4,
                            links: {
                                self: {
                                    method: 'GET',
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=25',
                                },
                                prev: {
                                    method: 'GET',
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=0',
                                },
                            },
                            reviews: [
                                {
                                    id: 3,
                                    links: {},
                                },
                                {
                                    id: 4,
                                    links: {},
                                },
                            ],
                        });
                    }
                });

                const result = collection.fetchAll();

                expect(result).toBe(true);
                expect($.ajax).toHaveBeenCalled();
                expect(numFetches).toBe(2);
                expect(collection.hasPrev).toBe(false);
                expect(collection.hasNext).toBe(false);
                expect(collection.totalResults).toBe(4);
                expect(collection.currentPage).toBe(0);
                expect(collection.length).toBe(4);
                expect(collection.at(0).id).toBe(1);
                expect(collection.at(1).id).toBe(2);
                expect(collection.at(2).id).toBe(3);
                expect(collection.at(3).id).toBe(4);
            });
        });

        describe('fetchNext', function() {
            it('With hasNext == false', function() {
                collection.hasNext = false;
                spyOn(collection, 'fetch');

                const result = collection.fetchNext();

                expect(result).toBe(false);
                expect(collection.fetch).not.toHaveBeenCalled();
            });

            it('With hasNext == true', function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/?start=25');
                    expect(request.type).toBe('GET');

                    request.success({
                        stat: 'ok',
                        total_results: 2,
                        links: {
                            self: {
                                method: 'GET',
                                href: '/api/review-requests/123/reviews/',
                            },
                            prev: {
                                method: 'GET',
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=0',
                            },
                            next: {
                                method: 'GET',
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=50',
                            },
                        },
                        reviews: [
                            {
                                id: 1,
                                links: {},
                            },
                            {
                                id: 2,
                                links: {},
                            },
                        ],
                    });
                });

                collection.hasNext = true;
                collection.currentPage = 2;
                collection._links = {
                    next: {
                        method: 'GET',
                        href: '/api/review-requests/123/reviews/?start=25',
                    },
                };

                spyOn(collection, 'fetch').and.callThrough();

                const result = collection.fetchNext();

                expect(result).toBe(true);
                expect(collection.fetch).toHaveBeenCalled();
                expect(collection.hasPrev).toBe(true);
                expect(collection.hasNext).toBe(true);
                expect(collection.currentPage).toBe(3);
                expect(collection.models.length).toBe(2);
            });
        });

        describe('fetchPrev', function() {
            it('With hasPrev == false', function() {
                collection.hasPrev = false;
                spyOn(collection, 'fetch');

                const result = collection.fetchPrev();

                expect(result).toBe(false);
                expect(collection.fetch).not.toHaveBeenCalled();
            });

            it('With hasPrev == true', function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/?start=25');
                    expect(request.type).toBe('GET');

                    request.success({
                        stat: 'ok',
                        total_results: 2,
                        links: {
                            self: {
                                method: 'GET',
                                href: '/api/review-requests/123/reviews/',
                            },
                            prev: {
                                method: 'GET',
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=0',
                            },
                            next: {
                                method: 'GET',
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=25',
                            },
                        },
                        reviews: [
                            {
                                id: 1,
                                links: {},
                            },
                            {
                                id: 2,
                                links: {},
                            },
                        ],
                    });
                });

                collection.hasPrev = true;
                collection.currentPage = 2;
                collection._links = {
                    prev: {
                        method: 'GET',
                        href: '/api/review-requests/123/reviews/?start=25',
                    },
                };

                spyOn(collection, 'fetch').and.callThrough();

                const result = collection.fetchPrev();

                expect(result).toBe(true);
                expect(collection.fetch).toHaveBeenCalled();
                expect(collection.hasPrev).toBe(true);
                expect(collection.hasNext).toBe(true);
                expect(collection.currentPage).toBe(1);
                expect(collection.models.length).toBe(2);
            });
        });

        describe('parse', function() {
            let payload;

            beforeEach(function() {
                payload = {
                    links: {},
                    total_results: 5,
                    reviews: [],
                };
            });

            it('Resources returned', function() {
                payload.reviews = [
                    { id: 1 },
                    { id: 2 },
                    { id: 3 },
                ];

                const results = collection.parse(payload);

                expect(results.length).toBe(3);
                expect(results[0].id).toBe(1);
                expect(results[1].id).toBe(2);
                expect(results[2].id).toBe(3);
            });

            it('totalResults set', function() {
                collection.parse(payload);
                expect(collection.totalResults).toBe(5);
            });

            describe('With fetchingAll', function() {
                const options = {
                    fetchingAll: true,
                };

                it('currentPage = 0', function() {
                    collection.parse(payload, options);
                    expect(collection.currentPage).toBe(0);
                });

                it('hasPrev disabled', function() {
                    collection.parse(payload, options);
                    expect(collection.hasPrev).toBe(false);
                });

                it('hasNext disabled', function() {
                    collection.parse(payload, options);
                    expect(collection.hasNext).toBe(false);
                });
            });

            describe('Without fetchingAll', function() {
                describe('currentPage', function() {
                    it('undefined when not options.page', function() {
                        collection.parse(payload);
                        expect(collection.currentPage).toBe(undefined);
                    });

                    it('Set when options.page', function() {
                        collection.parse(payload, {
                            page: 4,
                        });

                        expect(collection.currentPage).toBe(4);
                    });
                });

                describe('hasPrev', function() {
                    it('true with rsp.links.prev', function() {
                        payload.links = {
                            prev: {
                                href: 'blah',
                            },
                        };

                        collection.parse(payload);
                        expect(collection.hasPrev).toBe(true);
                    });

                    it('false without rsp.links.prev', function() {
                        collection.parse(payload);
                        expect(collection.hasPrev).toBe(false);
                    });
                });

                describe('hasNext', function() {
                    it('true with rsp.links.next', function() {
                        payload.links = {
                            next: {
                                href: 'blah',
                            },
                        };

                        collection.parse(payload);
                        expect(collection.hasNext).toBe(true);
                    });

                    it('false without rsp.links.next', function() {
                        collection.parse(payload);
                        expect(collection.hasNext).toBe(false);
                    });
                });
            });
        });

        describe('url', function() {
            it('With parentResource', function() {
                expect(collection.url())
                    .toBe('/api/review-requests/123/reviews/');
            });

            it('With _fetchURL', function() {
                collection._fetchURL = '/api/foo/';
                expect(collection.url()).toBe('/api/foo/');
            });

            it('Without _fetchURL or parentResource', function() {
                collection.parentResource = null;
                expect(collection.url()).toBe(null);
            });
        });
    });
});
