suite('rb/resources/models/ReviewRequest', function() {
    var reviewRequest,
        callbacks;

    beforeEach(function() {
        reviewRequest = new RB.ReviewRequest({
            id: 1
        });

        callbacks = {
            success: function() {},
            error: function() {}
        };

        spyOn(callbacks, 'success');
        spyOn(callbacks, 'error');

        spyOn(reviewRequest, 'ready').andCallFake(function(options, context) {
            options.ready.call(context);
        });
    });

    it('createDiff', function() {
        var diff = reviewRequest.createDiff();

        expect(diff.get('parentObject')).toBe(reviewRequest);
    });

    it('createScreenshot', function() {
        var screenshot = reviewRequest.createScreenshot(42);

        expect(screenshot.get('parentObject')).toBe(reviewRequest);
        expect(screenshot.id).toBe(42);
    });

    it('createFileAttachment', function() {
        var fileAttachment = reviewRequest.createFileAttachment({
            id: 42
        });

        expect(fileAttachment.get('parentObject')).toBe(reviewRequest);
        expect(fileAttachment.id).toBe(42);
    });

    it('parse', function() {
        console.log(reviewRequest);
        var data = reviewRequest.parse({
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
                testing_done_text_type: 'plain'
            }
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
        expect(data['public']).toBe('public');
        expect(data.summary).toBe('summary');
        expect(data.targetGroups).toBe('targetGroups');
        expect(data.targetPeople).toBe('targetPeople');
        expect(data.testingDone).toBe('testingDone');
        expect(data.testingDoneRichText).toBe(false);
    });

    it('reopen', function() {
        spyOn(RB, 'apiCall').andCallThrough();
        spyOn($, 'ajax').andCallFake(function(request) {
            expect(request.type).toBe('PUT');
            expect(request.data.status).toBe('pending');

            request.success({
                stat: 'ok',
                review_request: {
                    id: 1,
                    links: {}
                }
            });
        });

        reviewRequest.reopen({
            success: callbacks.success,
            error: callbacks.error
        });

        expect(RB.apiCall).toHaveBeenCalled();
        expect($.ajax).toHaveBeenCalled();
        expect(callbacks.success).toHaveBeenCalled();
        expect(callbacks.error).not.toHaveBeenCalled();
    });

    describe('createReview', function() {
        it('With review ID', function() {
            var review = reviewRequest.createReview(42);

            expect(review.get('parentObject')).toBe(reviewRequest);
            expect(review.get('id')).toBe(42);
            expect(reviewRequest.get('draftReview')).toBe(null);
            expect(reviewRequest.reviews.length).toBe(1);
            expect(reviewRequest.reviews.get(42)).toBe(review);
        });

        it('Without review ID', function() {
            var review1 = reviewRequest.createReview(),
                review2 = reviewRequest.createReview();

            expect(review1.get('parentObject')).toBe(reviewRequest);
            expect(review1.id).toBeFalsy();
            expect(reviewRequest.get('draftReview')).toBe(review1);
            expect(review1).toBe(review2);
            expect(reviewRequest.reviews.length).toBe(0);
        });
    });

    describe('setStarred', function() {
        var url = '/api/users/testuser/watched/review-requests/',
            session;

        beforeEach(function() {
            RB.UserSession.instance = null;
            session = RB.UserSession.create({
                username: 'testuser',
                watchedReviewRequestsURL: url
            });

            spyOn(session.watchedReviewRequests, 'addImmediately')
                .andCallThrough();
            spyOn(session.watchedReviewRequests, 'removeImmediately')
                .andCallThrough();
            spyOn(RB, 'apiCall').andCallThrough();
        });

        it('true', function() {
            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('POST');
                expect(request.url).toBe(url);

                request.success({
                    stat: 'ok'
                });
            });

            reviewRequest.setStarred(true, callbacks);

            expect(session.watchedReviewRequests.addImmediately)
                .toHaveBeenCalled();
            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('false', function() {
            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('DELETE');
                expect(request.url).toBe(url + '1/');

                request.success({
                    stat: 'ok'
                });
            });

            reviewRequest.setStarred(false, callbacks);

            expect(session.watchedReviewRequests.removeImmediately)
                .toHaveBeenCalled();
            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });
    });

    describe('close', function() {
        it('With type=CLOSE_DISCARDED', function() {
            spyOn(RB, 'apiCall').andCallThrough();
            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('PUT');
                expect(request.data.status).toBe('discarded');
                expect(request.data.description).toBe(undefined);

                request.success({
                    stat: 'ok',
                    review_request: {
                        id: 1,
                        links: {}
                    }
                });
            });

            reviewRequest.close({
                type: RB.ReviewRequest.CLOSE_DISCARDED,
                success: callbacks.success,
                error: callbacks.error
            });

            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('With type=CLOSE_SUBMITTED', function() {
            spyOn(RB, 'apiCall').andCallThrough();
            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('PUT');
                expect(request.data.status).toBe('submitted');
                expect(request.data.description).toBe(undefined);

                request.success({
                    stat: 'ok',
                    review_request: {
                        id: 1,
                        links: {}
                    }
                });
            });

            reviewRequest.close({
                type: RB.ReviewRequest.CLOSE_SUBMITTED,
                success: callbacks.success,
                error: callbacks.error
            });

            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });

        it('With invalid type', function() {
            spyOn(RB, 'apiCall').andCallThrough();
            spyOn($, 'ajax');

            reviewRequest.close({
                type: 'foo',
                success: callbacks.success,
                error: callbacks.error
            });

            expect(RB.apiCall).not.toHaveBeenCalled();
            expect($.ajax).not.toHaveBeenCalled();
            expect(callbacks.success).not.toHaveBeenCalled();
            expect(callbacks.error).toHaveBeenCalled();
        });

        it('With description', function() {
            spyOn(RB, 'apiCall').andCallThrough();
            spyOn($, 'ajax').andCallFake(function(request) {
                expect(request.type).toBe('PUT');
                expect(request.data.status).toBe('submitted');
                expect(request.data.close_description).toBe('test');

                request.success({
                    stat: 'ok',
                    review_request: {
                        id: 1,
                        links: {}
                    }
                });
            });

            reviewRequest.close({
                type: RB.ReviewRequest.CLOSE_SUBMITTED,
                description: 'test',
                success: callbacks.success,
                error: callbacks.error
            });

            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });
    });
});
