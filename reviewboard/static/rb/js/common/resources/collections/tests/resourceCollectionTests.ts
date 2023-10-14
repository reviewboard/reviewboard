import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    BaseCollection,
    ResourceCollection,
    Review,
} from 'reviewboard/common';


suite('rb/resources/collections/ResourceCollection', function() {
    let collection;
    let reviewRequest;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            id: 123,
            links: {
                reviews: {
                    href: '/api/review-requests/123/reviews/',
                },
            },
            loaded: true,
        });

        spyOn(reviewRequest, 'ready').and.resolveTo();

        collection = new ResourceCollection([], {
            model: Review,
            parentResource: reviewRequest,
        });
    });

    describe('Methods', function() {
        describe('fetch', function() {
            it('Populates collection', async function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/');
                    expect(request.type).toBe('GET');

                    request.success({
                        links: {
                            next: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=25',
                                method: 'GET',
                            },
                            self: {
                                href: '/api/review-requests/123/reviews/',
                                method: 'GET',
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
                        stat: 'ok',
                        total_results: 2,
                    });
                });

                await collection.fetch();

                expect($.ajax).toHaveBeenCalled();
                expect(collection.length).toBe(2);
                expect(collection.at(0).id).toBe(1);
                expect(collection.at(1).id).toBe(2);
                expect(collection.hasPrev).toBe(false);
                expect(collection.hasNext).toBe(true);
            });

            it('With start=', async function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/');
                    expect(request.data).not.toBe(undefined);
                    expect(request.data.start).toBe(100);

                    request.success({});
                });

                await collection.fetch({ start: 100 });

                const ajaxOpts = $.ajax.calls.argsFor(0)[0];
                expect(ajaxOpts.type).toBe('GET');
                expect(ajaxOpts.url)
                    .toBe('/api/review-requests/123/reviews/');
                expect(ajaxOpts.start).toBe(100);
                expect(ajaxOpts.data).toEqual({
                    api_format: 'json',
                    start: 100,
                });
            });

            describe('With parentResource', function() {
                it('Calls parentResource.ready', async function() {
                    spyOn(BaseCollection.prototype, 'fetch')
                        .and.resolveTo();

                    await collection.fetch();

                    expect(reviewRequest.ready).toHaveBeenCalled();
                    expect(BaseCollection.prototype.fetch)
                        .toHaveBeenCalled();
                });
            });

            it('Using callbacks', function(done) {
                spyOn(BaseCollection.prototype, 'fetch')
                    .and.resolveTo();
                spyOn(console, 'warn');

                collection.fetch({
                    error: () => done.fail(),
                    success: () => {
                        expect(reviewRequest.ready).toHaveBeenCalled();
                        expect(BaseCollection.prototype.fetch)
                            .toHaveBeenCalled();
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                });
            });
        });

        describe('fetchAll', function() {
            it('Spanning pages', async function() {
                let numFetches = 0;

                spyOn($, 'ajax').and.callFake(request => {
                    console.assert(numFetches < 2);

                    expect(request.type).toBe('GET');

                    numFetches++;

                    if (numFetches === 1) {
                        expect(request.url).toBe(
                            '/api/review-requests/123/reviews/');

                        request.success({
                            links: {
                                next: {
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=25',
                                    method: 'GET',
                                },
                                self: {
                                    href: '/api/review-requests/123/reviews/',
                                    method: 'GET',
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
                            stat: 'ok',
                            total_results: 4,
                        });
                    } else if (numFetches === 2) {
                        expect(request.url).toBe(
                            '/api/review-requests/123/reviews/?start=25');

                        request.success({
                            links: {
                                prev: {
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=0',
                                    method: 'GET',
                                },
                                self: {
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=25',
                                    method: 'GET',
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
                            stat: 'ok',
                            total_results: 4,
                        });
                    }
                });

                await collection.fetchAll();

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

            it('With callbacks', function(done) {
                let numFetches = 0;

                spyOn($, 'ajax').and.callFake(request => {
                    console.assert(numFetches < 2);

                    expect(request.type).toBe('GET');

                    numFetches++;

                    if (numFetches === 1) {
                        expect(request.url).toBe(
                            '/api/review-requests/123/reviews/');

                        request.success({
                            links: {
                                next: {
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=25',
                                    method: 'GET',
                                },
                                self: {
                                    href: '/api/review-requests/123/reviews/',
                                    method: 'GET',
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
                            stat: 'ok',
                            total_results: 4,
                        });
                    } else if (numFetches === 2) {
                        expect(request.url).toBe(
                            '/api/review-requests/123/reviews/?start=25');

                        request.success({
                            links: {
                                prev: {
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=0',
                                    method: 'GET',
                                },
                                self: {
                                    href: '/api/review-requests/123/reviews/' +
                                          '?start=25',
                                    method: 'GET',
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
                            stat: 'ok',
                            total_results: 4,
                        });
                    }
                });

                spyOn(console, 'warn');

                collection.fetchAll({
                    error: () => done.fail(),
                    success: () => {
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
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                });
            });
        });

        describe('fetchNext', function() {
            it('With hasNext == false', async function() {
                collection.hasNext = false;
                spyOn(collection, 'fetch');

                await collection.fetchNext();

                expect(collection.fetch).not.toHaveBeenCalled();
            });

            it('With hasNext == true', async function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/?start=25');
                    expect(request.type).toBe('GET');

                    request.success({
                        links: {
                            next: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=50',
                                method: 'GET',
                            },
                            prev: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=0',
                                method: 'GET',
                            },
                            self: {
                                href: '/api/review-requests/123/reviews/',
                                method: 'GET',
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
                        stat: 'ok',
                        total_results: 2,
                    });
                });

                collection.hasNext = true;
                collection.currentPage = 2;
                collection._links = {
                    next: {
                        href: '/api/review-requests/123/reviews/?start=25',
                        method: 'GET',
                    },
                };

                spyOn(collection, 'fetch').and.callThrough();

                await collection.fetchNext();

                expect(collection.fetch).toHaveBeenCalled();
                expect(collection.hasPrev).toBe(true);
                expect(collection.hasNext).toBe(true);
                expect(collection.currentPage).toBe(3);
                expect(collection.models.length).toBe(2);
            });

            it('With callbacks', function(done) {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/?start=25');
                    expect(request.type).toBe('GET');

                    request.success({
                        links: {
                            next: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=50',
                                method: 'GET',
                            },
                            prev: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=0',
                                method: 'GET',
                            },
                            self: {
                                href: '/api/review-requests/123/reviews/',
                                method: 'GET',
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
                        stat: 'ok',
                        total_results: 2,
                    });
                });

                collection.hasNext = true;
                collection.currentPage = 2;
                collection._links = {
                    next: {
                        href: '/api/review-requests/123/reviews/?start=25',
                        method: 'GET',
                    },
                };

                spyOn(collection, 'fetch').and.callThrough();
                spyOn(console, 'warn');

                collection.fetchNext({
                    error: () => done.fail(),
                    success: () => {
                        expect(collection.fetch).toHaveBeenCalled();
                        expect(collection.hasPrev).toBe(true);
                        expect(collection.hasNext).toBe(true);
                        expect(collection.currentPage).toBe(3);
                        expect(collection.models.length).toBe(2);
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                });
            });
        });

        describe('fetchPrev', function() {
            it('With hasPrev == false', async function() {
                collection.hasPrev = false;
                spyOn(collection, 'fetch');

                await collection.fetchPrev();

                expect(collection.fetch).not.toHaveBeenCalled();
            });

            it('With hasPrev == true', async function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/?start=25');
                    expect(request.type).toBe('GET');

                    request.success({
                        links: {
                            next: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=25',
                                method: 'GET',
                            },
                            prev: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=0',
                                method: 'GET',
                            },
                            self: {
                                href: '/api/review-requests/123/reviews/',
                                method: 'GET',
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
                        stat: 'ok',
                        total_results: 2,
                    });
                });

                collection.hasPrev = true;
                collection.currentPage = 2;
                collection._links = {
                    prev: {
                        href: '/api/review-requests/123/reviews/?start=25',
                        method: 'GET',
                    },
                };

                spyOn(collection, 'fetch').and.callThrough();

                await collection.fetchPrev();

                expect(collection.fetch).toHaveBeenCalled();
                expect(collection.hasPrev).toBe(true);
                expect(collection.hasNext).toBe(true);
                expect(collection.currentPage).toBe(1);
                expect(collection.models.length).toBe(2);
            });

            it('With callbacks', function(done) {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.url).toBe(
                        '/api/review-requests/123/reviews/?start=25');
                    expect(request.type).toBe('GET');

                    request.success({
                        links: {
                            next: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=25',
                                method: 'GET',
                            },
                            prev: {
                                href: '/api/review-requests/123/reviews/' +
                                      '?start=0',
                                method: 'GET',
                            },
                            self: {
                                href: '/api/review-requests/123/reviews/',
                                method: 'GET',
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
                        stat: 'ok',
                        total_results: 2,
                    });
                });

                collection.hasPrev = true;
                collection.currentPage = 2;
                collection._links = {
                    prev: {
                        href: '/api/review-requests/123/reviews/?start=25',
                        method: 'GET',
                    },
                };

                spyOn(collection, 'fetch').and.callThrough();
                spyOn(console, 'warn');

                collection.fetchPrev({
                    error: () => done.fail(),
                    success: () => {
                        expect(collection.fetch).toHaveBeenCalled();
                        expect(collection.hasPrev).toBe(true);
                        expect(collection.hasNext).toBe(true);
                        expect(collection.currentPage).toBe(1);
                        expect(collection.models.length).toBe(2);
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                });
            });
        });

        describe('parse', function() {
            let payload;

            beforeEach(function() {
                payload = {
                    links: {},
                    reviews: [],
                    total_results: 5,
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
