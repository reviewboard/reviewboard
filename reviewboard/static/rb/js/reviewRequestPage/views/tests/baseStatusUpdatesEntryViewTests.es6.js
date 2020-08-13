suite('rb/reviewRequestPage/views/BaseStatusUpdatesEntryView', function() {
    /* It's much easier to test against a stub than the full page. */
    const TestPage = Backbone.View.extend({
        stopWatchingEntryUpdates() {},
        watchEntryUpdates() {},
        queueLoadDiff() {},
    });

    const statusUpdateHTML = dedent`
        <div id="initial_status_updates"
             class="review-request-page-entry status-updates">
         <a name="initial_status_updates"></a>
         <div class="review-request-page-entry-contents">
          <div class="header status-update-state-pending">
           <div class="collapse-button btn">
            <div class="rb-icon rb-icon-collapse-review"></div>
           </div>
           <div class="header-details">
            <div class="summary">
             <span class="review-request-page-entry-title">
              Checks run (1 waiting to run)
             </span>
            </div>
            <a href="#initial_status_updates" class="timestamp">
             <time class="timesince"
                   datetime="2018-11-27T00:18:43.664524+00:00"
                   title="Nov. 27, 2018, 12:18 a.m.">0 minutes ago</time>
            </a>
           </div>
          </div>
          <div class="banners"></div>
          <div class="body">
           <section class="status-update-summary">
            <div class="status-update-summary-entry
             status-update-state-not-yet-run">
             <span class="summary">nyc</span>
             Waiting to run
             <input type="button" value="Run" class="status-update-request-run"
                    data-status-update-id="1">
            </div>
           </section>
          </div>
         </div>
        </div>
    `;

    let entryView;
    let page;
    let entry;

    beforeEach(function() {
        const reviewRequest = new RB.ReviewRequest({ id: 5 });
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
            localSitePrefix: null,
            reviewRequest: reviewRequest,
            reviewRequestEditor: editor,
            reviewRequestId: 5,
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

        const $el = $(statusUpdateHTML).appendTo($testsScratch);

        entryView = new RB.ReviewRequestPage.BaseStatusUpdatesEntryView({
            el: $el,
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

    describe('Run status update', function() {
        it('Runs and checks for updates when button is clicked', function() {
            spyOn(entryView.model, 'stopWatchingUpdates');
            spyOn(entryView.model, 'watchUpdates');
            spyOn(RB, 'apiCall').and.callThrough();
            spyOn($, 'ajax').and.callFake(request => {
                expect(request.type).toBe('PUT');
                expect(request.url).toBe('/api/review-requests/5/status-updates/1/');
                request.success();
            });

            entryView.$el.find('.status-update-request-run').first().click();

            expect(RB.apiCall).toHaveBeenCalled();
            expect($.ajax).toHaveBeenCalled();
            expect(entryView.model.stopWatchingUpdates).toHaveBeenCalled();
            expect(entryView.model.watchUpdates).toHaveBeenCalled();
        });
    });
});
