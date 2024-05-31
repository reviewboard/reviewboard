import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    API,
    ReviewGroup,
    UserSession,
} from 'reviewboard/common';


suite('rb/resources/models/ReviewGroup', function() {
    describe('setStarred', function() {
        const url = '/api/users/testuser/watched/groups/';
        let group: ReviewGroup;
        let session: UserSession;

        beforeEach(function() {
            UserSession.instance = null;
            session = UserSession.create({
                username: 'testuser',
                watchedReviewGroupsURL: url,
            });

            group = new ReviewGroup({
                id: 1,
            });

            spyOn(session.watchedGroups, 'addImmediately').and.callThrough();
            spyOn(session.watchedGroups, 'removeImmediately')
                .and.callThrough();
            spyOn(API, 'request').and.callThrough();
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
            expect(API.request).toHaveBeenCalled();
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
            expect(API.request).toHaveBeenCalled();
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
                error: () => done.fail(),
                success: () => {
                    expect(session.watchedGroups.addImmediately)
                        .toHaveBeenCalled();
                    expect(API.request).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
            });
        });
    });

    describe('addUser', function() {
        let group: ReviewGroup;

        beforeEach(function() {
            group = new ReviewGroup({
                id: 1,
                name: 'test-group',
            });

            spyOn(API, 'request').and.callThrough();
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
            expect(API.request).toHaveBeenCalled();
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
                error: () => done.fail(),
                success: () => {
                    expect(API.request).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
            });
        });

        it('Unloaded group', async function() {
            spyOn($, 'ajax');

            group.set('id', null);
            expect(group.isNew()).toBe(true);

            await expectAsync(group.addUser('my-user')).toBeRejectedWith(
                Error('Unable to add to the group.'));

            expect(API.request).not.toHaveBeenCalled();
            expect($.ajax).not.toHaveBeenCalled();
        });
    });

    describe('removeUser', function() {
        let group: ReviewGroup;

        beforeEach(function() {
            group = new ReviewGroup({
                id: 1,
                name: 'test-group',
            });

            spyOn(API, 'request').and.callThrough();
        });

        it('Loaded group', async function() {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('DELETE');

                request.success();
            });

            await group.removeUser('my-user');
            expect(API.request).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
        });

        it('With callbacks', function(done) {
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('DELETE');

                request.success();
            });
            spyOn(console, 'warn');

            group.removeUser('my-user', {
                error: () => done.fail(),
                success: () => {
                    expect(API.request).toHaveBeenCalled();
                    expect($.ajax).toHaveBeenCalled();
                    expect(console.warn).toHaveBeenCalled();

                    done();
                },
            });
        });

        it('Unloaded group', async function() {
            spyOn($, 'ajax');

            group.set('id', null);
            expect(group.isNew()).toBe(true);

            await expectAsync(group.removeUser('my-user')).toBeRejectedWith(
                Error('Unable to remove from the group.'));

            expect(API.request).not.toHaveBeenCalled();
            expect($.ajax).not.toHaveBeenCalled();
        });
    });
});
