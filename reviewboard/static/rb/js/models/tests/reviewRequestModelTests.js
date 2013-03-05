describe('models/ReviewRequest', function() {
    describe('setStarred', function() {
        var url = '/api/users/testuser/watched/review-requests/',
            callbacks,
            session,
            reviewRequest;

        beforeEach(function() {
            session = RB.UserSession.create({
                username: 'testuser',
                watchedReviewRequestsURL: url
            });

            reviewRequest = new RB.ReviewRequest(1);

            callbacks = {
                success: function() {},
                error: function() {}
            };

            spyOn(session.watchedReviewRequests, 'addImmediately')
                .andCallThrough();
            spyOn(session.watchedReviewRequests, 'removeImmediately')
                .andCallThrough();
            spyOn(RB, 'apiCall').andCallThrough();
            spyOn(callbacks, 'success');
            spyOn(callbacks, 'error');
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
});
