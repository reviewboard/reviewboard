describe('resources/models/ReviewGroup', function() {
    describe('setStarred', function() {
        var url = '/api/users/testuser/watched/groups/',
            callbacks,
            session,
            group;

        beforeEach(function() {
            RB.UserSession.instance = null;
            session = RB.UserSession.create({
                username: 'testuser',
                watchedReviewGroupsURL: url
            });

            group = new RB.ReviewGroup({
                id: 1
            });

            callbacks = {
                success: function() {},
                error: function() {}
            };

            spyOn(session.watchedGroups, 'addImmediately').andCallThrough();
            spyOn(session.watchedGroups, 'removeImmediately').andCallThrough();
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

            group.setStarred(true, callbacks);

            expect(session.watchedGroups.addImmediately).toHaveBeenCalled();
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

            group.setStarred(false, callbacks);

            expect(session.watchedGroups.removeImmediately).toHaveBeenCalled();
            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalled();
            expect(callbacks.error).not.toHaveBeenCalled();
        });
    });
});
