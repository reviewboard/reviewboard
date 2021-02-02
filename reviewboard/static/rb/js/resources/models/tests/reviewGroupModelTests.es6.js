suite('rb/resources/models/ReviewGroup', function() {
    describe('setStarred', function() {
        const url = '/api/users/testuser/watched/groups/';
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

            spyOn(session.watchedGroups, 'addImmediately').and.callThrough();
            spyOn(session.watchedGroups, 'removeImmediately').and.callThrough();
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

            await group.setStarred(true);

            expect(session.watchedGroups.addImmediately)
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

            await group.setStarred(false);

            expect(session.watchedGroups.removeImmediately)
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

            group.setStarred(true, {
                success: () => {
                    expect(session.watchedGroups.addImmediately)
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

        it('Loaded group', function(done) {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('POST');
                expect(request.data.username).toBe('my-user');

                request.success({
                    stat: 'ok',
                });
            });

            callbacks.success.and.callFake(() => {
                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();

                done();
            });
            callbacks.error.and.callFake(() => done.fail());

            group.addUser('my-user', callbacks);
        });

        it('Unloaded group', function(done) {
            spyOn($, 'ajax');

            group.set('id', null);
            expect(group.isNew()).toBe(true);

            callbacks.success.and.callFake(() => done.fail());
            callbacks.error.and.callFake(() => {
                expect(RB.apiCall).not.toHaveBeenCalled();
                expect($.ajax).not.toHaveBeenCalled();

                done();
            });

            group.addUser('my-user', callbacks);
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

            callbacks.success.and.callFake(() => {
                expect(RB.apiCall).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();
                done();
            });

            group.removeUser('my-user', callbacks);
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
