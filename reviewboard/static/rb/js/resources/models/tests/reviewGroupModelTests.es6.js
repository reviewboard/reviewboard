suite('rb/resources/models/ReviewGroup', function() {
    describe('setStarred', function() {
        const url = '/api/users/testuser/watched/groups/';
        let callbacks;
        let group;
        let session;

        beforeEach(function() {
            RB.UserSession.instance = null;
            session = RB.UserSession.create({
                username: 'testuser',
                watchedReviewGroupsURL: url,
            });

            group = new RB.ReviewGroup({
                id: 1,
            });

            callbacks = {
                success: function() {},
                error: function() {},
            };

            spyOn(session.watchedGroups, 'addImmediately').and.callThrough();
            spyOn(session.watchedGroups, 'removeImmediately').and.callThrough();
            spyOn(RB, 'apiCall').and.callThrough();
            spyOn(callbacks, 'success');
            spyOn(callbacks, 'error');
        });

        it('true', function() {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('POST');
                expect(request.url).toBe(url);

                request.success({
                    stat: 'ok',
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
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('DELETE');
                expect(request.url).toBe(url + '1/');

                request.success({
                    stat: 'ok',
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

    describe('addUser', function() {
        let callbacks;
        let group;

        beforeEach(function() {
            group = new RB.ReviewGroup({
                id: 1,
                name: 'test-group',
            });

            callbacks = {
                success: function() {},
                error: function() {},
            };

            spyOn(RB, 'apiCall').and.callThrough();
            spyOn(callbacks, 'success');
            spyOn(callbacks, 'error');
        });

        it('Loaded group', function() {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('POST');
                expect(request.data.username).toBe('my-user');

                request.success({
                    stat: 'ok',
                });
            });

            group.addUser('my-user', callbacks);

            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalled();
        });

        it('Unloaded group', function() {
            spyOn($, 'ajax');

            group.set('id', null);
            expect(group.isNew()).toBe(true);

            group.addUser('my-user', callbacks);

            expect(RB.apiCall).not.toHaveBeenCalled();
            expect($.ajax).not.toHaveBeenCalled();
            expect(callbacks.error).toHaveBeenCalled();
        });
    });

    describe('removeUser', function() {
        let callbacks;
        let group;

        beforeEach(function() {
            group = new RB.ReviewGroup({
                id: 1,
                name: 'test-group',
            });

            callbacks = {
                success: function() {},
                error: function() {},
            };

            spyOn(RB, 'apiCall').and.callThrough();
            spyOn(callbacks, 'success');
            spyOn(callbacks, 'error');
        });

        it('Loaded group', function() {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('DELETE');

                request.success();
            });

            group.removeUser('my-user', callbacks);

            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(callbacks.success).toHaveBeenCalled();
        });

        it('Unloaded group', function() {
            spyOn($, 'ajax');

            group.set('id', null);
            expect(group.isNew()).toBe(true);

            group.removeUser('my-user', callbacks);

            expect(RB.apiCall).not.toHaveBeenCalled();
            expect($.ajax).not.toHaveBeenCalled();
            expect(callbacks.error).toHaveBeenCalled();
        });
    });
});
