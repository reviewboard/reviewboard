suite('rb/reviewRequestPage/views/BaseStatusUpdatesEntryView', function() {
    /* It's much easier to test against a stub than the full page. */
    const TestPage = Backbone.View.extend({
        stopWatchingEntryUpdates() {},
        watchEntryUpdates() {},
        queueLoadDiff() {},
    });

    let entryView;
    let page;
    let entry;

    beforeEach(function() {
        const reviewRequest = new RB.ReviewRequest();
        const editor = new RB.ReviewRequestEditor({
            reviewRequest: reviewRequest
        });

        entry = new RB.ReviewRequestPage.StatusUpdatesEntry({
            reviews: [
                reviewRequest.createReview(100, {
                    loaded: true,
                    links: {
                        replies: {
                            href: '/api/review/100/replies/'
                        }
                    }
                }),
                reviewRequest.createReview(101, {
                    loaded: true,
                    links: {
                        replies: {
                            href: '/api/review/101/replies/'
                        }
                    }
                }),
            ],
            reviewRequest: reviewRequest,
            reviewRequestEditor: editor,
            id: '0',
            typeID: 'initial_status_updates',
            addedTimestamp: new Date(Date.UTC(2017, 7, 18, 13, 40, 25)),
            updatedTimestamp: new Date(Date.UTC(2017, 7, 18, 16, 20, 0)),
            pendingStatusUpdates: true,
            diffCommentsData: [
                ['1', '100'],
                ['2', '100-101'],
            ],
        });

        entryView = new RB.ReviewRequestPage.BaseStatusUpdatesEntryView({
            model: entry,
        });

        page = new TestPage();
        page.diffFragmentQueue = new RB.DiffFragmentQueueView({
            containerPrefix: 'comment',
        });
        entry.set('page', page);
        RB.PageManager.setPage(page);
    });

    afterEach(function() {
        RB.PageManager.setPage(null);
    });

    describe('Dynamic Updating', function() {
        describe('Update checking', function() {
            it('Enabled when pendingStatusUpdates=true', function() {
                spyOn(entry, 'watchUpdates');

                entry.set('pendingStatusUpdates', true);
                entryView.render();

                expect(entry.watchUpdates).toHaveBeenCalled();
            });

            it('Disabled when pendingStatusUpdates=false', function() {
                spyOn(entry, 'watchUpdates');

                entry.set('pendingStatusUpdates', false);
                entryView.render();

                expect(entry.watchUpdates).not.toHaveBeenCalled();
            });
        });

        it('Saves fragments on beforeApplyUpdate', function() {
            spyOn(page.diffFragmentQueue, 'saveFragment');
            spyOn(page, 'stopWatchingEntryUpdates');

            entryView.beforeApplyUpdate();
            expect(page.diffFragmentQueue.saveFragment.calls.count()).toBe(2);
            expect(page.diffFragmentQueue.saveFragment.calls.argsFor(0))
                .toEqual(['1']);
            expect(page.diffFragmentQueue.saveFragment.calls.argsFor(1))
                .toEqual(['2']);
            expect(page.stopWatchingEntryUpdates).toHaveBeenCalled();
        });
    });

    describe('render', function() {
        it('Creates ReviewViews', function() {
            entryView.render();

            expect(entryView._reviewViews.length).toBe(2);
        });
    });
});
