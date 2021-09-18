suite('rb/resources/models/ReviewRequest', function() {
    let reviewRequest;

    describe('Create from commit ID', function() {
        beforeEach(function() {
            reviewRequest = new RB.ReviewRequest();

            spyOn($, 'ajax').and.callFake(request => {
                expect(request.data.commit_id).toBe('test');
                expect(request.data.create_from_commit_id).toBe(true);

                request.success({});
            });
        });

        it('With promises', async function() {
            await reviewRequest.createFromCommit('test');
        });

        it('With callbacks', function(done) {
            spyOn(console, 'warn');

            reviewRequest.createFromCommit({
                commitID: 'test',
                success: () => {
                    expect(console.warn).toHaveBeenCalled();
                    done();
                },
                error: () => done.fail(),
            });
        });
    });

    describe('Existing instance', function() {
        beforeEach(function() {
            reviewRequest = new RB.ReviewRequest({
                id: 1,
            });

            spyOn(reviewRequest, 'ready').and.resolveTo();
        });

        it('createDiff', function() {
            const diff = reviewRequest.createDiff();

            expect(diff.get('parentObject')).toBe(reviewRequest);
        });

        it('createScreenshot', function() {
            const screenshot = reviewRequest.createScreenshot(42);

            expect(screenshot.get('parentObject')).toBe(reviewRequest);
            expect(screenshot.id).toBe(42);
        });

        it('createFileAttachment', function() {
            const fileAttachment = reviewRequest.createFileAttachment({
                id: 42,
            });

            expect(fileAttachment.get('parentObject')).toBe(reviewRequest);
            expect(fileAttachment.id).toBe(42);
        });

        it('parse', function() {
            const data = reviewRequest.parse({
                stat: 'ok',
                review_request: {
                    id: 1,
                    branch: 'branch',
                    bugs_closed: 'bugsClosed',
                    close_description: 'closeDescription',
                    close_description_text_type: 'markdown',
                    description: 'description',
                    description_text_type: 'markdown',
                    last_updated: 'lastUpdated',
                    'public': 'public',
                    summary: 'summary',
                    target_groups: 'targetGroups',
                    target_people: 'targetPeople',
                    testing_done: 'testingDone',
                    testing_done_text_type: 'plain',
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(1);
            expect(data.branch).toBe('branch');
            expect(data.bugsClosed).toBe('bugsClosed');
            expect(data.closeDescription).toBe('closeDescription');
            expect(data.closeDescriptionRichText).toBe(true);
            expect(data.description).toBe('description');
            expect(data.descriptionRichText).toBe(true);
            expect(data.lastUpdated).toBe('lastUpdated');
            expect(data.public).toBe('public');
            expect(data.summary).toBe('summary');
            expect(data.targetGroups).toBe('targetGroups');
            expect(data.targetPeople).toBe('targetPeople');
            expect(data.testingDone).toBe('testingDone');
            expect(data.testingDoneRichText).toBe(false);
        });

        describe('reopen', function() {
            it('With promises', async function() {
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('PUT');
                    expect(request.data.status).toBe('pending');

                    request.success({
                        stat: 'ok',
                        review_request: {
                            id: 1,
                            links: {},
                        },
                    });
                });

                await reviewRequest.reopen();

                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });

            it('With callbacks', function(done) {
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('PUT');
                    expect(request.data.status).toBe('pending');

                    request.success({
                        stat: 'ok',
                        review_request: {
                            id: 1,
                            links: {},
                        },
                    });
                });
                spyOn(console, 'warn');

                reviewRequest.reopen({
                    success: () => {
                        expect(RB.apiCall).toHaveBeenCalled();
                        expect($.ajax).toHaveBeenCalled();
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                    error: () => done.fail(),
                });
            });
        });

        describe('createReview', function() {
            it('With review ID', function() {
                const review = reviewRequest.createReview(42);

                expect(review.get('parentObject')).toBe(reviewRequest);
                expect(review.get('id')).toBe(42);
                expect(reviewRequest.get('draftReview')).toBe(null);
                expect(reviewRequest.reviews.length).toBe(1);
                expect(reviewRequest.reviews.get(42)).toBe(review);
            });

            it('Without review ID', function() {
                const review1 = reviewRequest.createReview();
                const review2 = reviewRequest.createReview();

                expect(review1.get('parentObject')).toBe(reviewRequest);
                expect(review1.id).toBeFalsy();
                expect(reviewRequest.get('draftReview')).toBe(review1);
                expect(review1).toBe(review2);
                expect(reviewRequest.reviews.length).toBe(0);
            });
        });

        describe('setStarred', function() {
            const url = '/api/users/testuser/watched/review-requests/';
            let session;

            beforeEach(function() {
                RB.UserSession.instance = null;
                session = RB.UserSession.create({
                    username: 'testuser',
                    watchedReviewRequestsURL: url,
                });

                spyOn(session.watchedReviewRequests, 'addImmediately')
                    .and.callThrough();
                spyOn(session.watchedReviewRequests, 'removeImmediately')
                    .and.callThrough();
                spyOn(RB, 'apiCall').and.callThrough();
            });

            it('true', async function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('POST');
                    expect(request.url).toBe(url);

                    request.success({
                        stat: 'ok',
                    });
                });

                await reviewRequest.setStarred(true);

                expect(session.watchedReviewRequests.addImmediately)
                    .toHaveBeenCalled();
                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });

            it('false', async function() {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('DELETE');
                    expect(request.url).toBe(url + '1/');

                    request.success({
                        stat: 'ok',
                    });
                });

                await reviewRequest.setStarred(false);

                expect(session.watchedReviewRequests.removeImmediately)
                    .toHaveBeenCalled();
                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });

            it('With callbacks', function(done) {
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('POST');
                    expect(request.url).toBe(url);

                    request.success({
                        stat: 'ok',
                    });
                });
                spyOn(console, 'warn');

                reviewRequest.setStarred(true, {
                    success: () => {
                        expect(session.watchedReviewRequests.addImmediately)
                            .toHaveBeenCalled();
                        expect(RB.apiCall).toHaveBeenCalled();
                        expect($.ajax).toHaveBeenCalled();
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                    error: () => done.fail(),
                });
            });
        });

        describe('close', function() {
            it('With type=CLOSE_DISCARDED', async function() {
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('PUT');
                    expect(request.data.status).toBe('discarded');
                    expect(request.data.description).toBe(undefined);

                    request.success({
                        stat: 'ok',
                        review_request: {
                            id: 1,
                            links: {},
                        },
                    });
                });

                await reviewRequest.close({
                    type: RB.ReviewRequest.CLOSE_DISCARDED,
                });

                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });

            it('With type=CLOSE_SUBMITTED', async function() {
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('PUT');
                    expect(request.data.status).toBe('submitted');
                    expect(request.data.description).toBe(undefined);

                    request.success({
                        stat: 'ok',
                        review_request: {
                            id: 1,
                            links: {},
                        }
                    });
                });

                await reviewRequest.close({
                    type: RB.ReviewRequest.CLOSE_SUBMITTED,
                });

                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });

            it('With invalid type', async function() {
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax');

                await expectAsync(reviewRequest.close({type: 'foo'})).
                    toBeRejectedWith(Error('Invalid close type'));

                expect(RB.apiCall).not.toHaveBeenCalled();
                expect($.ajax).not.toHaveBeenCalled();
            });

            it('With description', async function() {
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('PUT');
                    expect(request.data.status).toBe('submitted');
                    expect(request.data.close_description).toBe('test');

                    request.success({
                        stat: 'ok',
                        review_request: {
                            id: 1,
                            links: {},
                        },
                    });
                });

                await reviewRequest.close({
                    type: RB.ReviewRequest.CLOSE_SUBMITTED,
                    description: 'test',
                });

                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
            });

            it('With callbacks', function(done) {
                spyOn(RB, 'apiCall').and.callThrough();
                spyOn($, 'ajax').and.callFake(request => {
                    expect(request.type).toBe('PUT');
                    expect(request.data.status).toBe('discarded');
                    expect(request.data.description).toBe(undefined);

                    request.success({
                        stat: 'ok',
                        review_request: {
                            id: 1,
                            links: {},
                        },
                    });
                });
                spyOn(console, 'warn');

                reviewRequest.close({
                    type: RB.ReviewRequest.CLOSE_DISCARDED,
                    success: () => {
                        expect(RB.apiCall).toHaveBeenCalled();
                        expect($.ajax).toHaveBeenCalled();
                        expect(console.warn).toHaveBeenCalled();

                        done();
                    },
                    error: () => done.fail(),
                });
            });
        });
    });
});
