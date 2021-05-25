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
        let group;

        beforeEach(function() {
            group = new RB.ReviewGroup({
                id: 1,
                name: 'test-group',
            });

            spyOn(RB, 'apiCall').and.callThrough();
        });

        it('Loaded group', async function() {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('POST');
                expect(request.data.username).toBe('my-user');

                request.success({
                    stat: 'ok',
                });
            });

            await group.addUser('my-user');
            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
        });

        it('With callbacks', function(done) {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('POST');
                expect(request.data.username).toBe('my-user');

                request.success({
                    stat: 'ok',
                });
            });
            spyOn(console, 'warn');

            group.addUser('my-user', {
                success: () => {
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
                error: () => done.fail(),
            });
        });

        it('Unloaded group', async function() {
            spyOn($, 'ajax');

            group.set('id', null);
            expect(group.isNew()).toBe(true);

            await expectAsync(group.addUser('my-user')).toBeRejectedWith(
                Error('Unable to add to the group.'));

            expect(RB.apiCall).not.toHaveBeenCalled();
            expect($.ajax).not.toHaveBeenCalled();
        });
    });

    describe('removeUser', function() {
        let group;

        beforeEach(function() {
            group = new RB.ReviewGroup({
                id: 1,
                name: 'test-group',
            });

            spyOn(RB, 'apiCall').and.callThrough();
        });

        it('Loaded group', async function() {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('DELETE');

                request.success();
            });

            await group.removeUser('my-user');
            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
        });

        it('With callbacks', function(done) {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('DELETE');

                request.success();
            });
            spyOn(console, 'warn');

            group.removeUser('my-user', {
                success: () => {
                    expect(RB.apiCall).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
                error: () => done.fail(),
            });
        });

        it('Unloaded group', async function() {
            spyOn($, 'ajax');

            group.set('id', null);
            expect(group.isNew()).toBe(true);

            expectAsync(group.removeUser('my-user')).toBeRejectedWith(
                Error('Unable to remove from the group.'));

            expect(RB.apiCall).not.toHaveBeenCalled();
            expect($.ajax).not.toHaveBeenCalled();
        });
    });
});
