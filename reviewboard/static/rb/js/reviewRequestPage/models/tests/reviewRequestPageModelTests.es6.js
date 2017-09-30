suite('rb/reviewRequestPage/models/ReviewRequestPage', function() {
    let page;

    beforeEach(function() {
        page = new RB.ReviewRequestPage.ReviewRequestPage({
            updatesURL: '/r/123/_updates/',
            checkForUpdates: false,
            reviewRequestData: {},
            editorData: {
                fileAttachments: [],
                mutableByUser: true,
                showSendEmail: false,
            },
        }, {
            parse: true,
        });
    });

    describe('Methods', function() {
        it('addEntry', function() {
            const entry = new RB.ReviewRequestPage.Entry();

            page.addEntry(entry);

            expect(entry.get('page')).toBe(page);
            expect(page.entries.at(0)).toBe(entry);
        });

        describe('parse', function() {
            it('Parent called', function() {
                const attrs = page.parse({
                    reviewRequestData: {
                        summary: 'Test summary',
                    },
                });

                expect(attrs.reviewRequest).toBeTruthy();
                expect(attrs.reviewRequest.get('summary')).toBe('Test summary');
            });

            it('updatesURL', function() {
                const attrs = page.parse({
                    updatesURL: 'https://example.com/',
                });

                expect(attrs.updatesURL).toBe('https://example.com/');
            });
        });

        describe('watchEntryUpdates', function() {
            let entry;

            beforeEach(function() {
                spyOn(page, '_scheduleCheckUpdates');

                entry = new RB.ReviewRequestPage.Entry({
                    id: 'my-entry',
                });
            });

            it('First call', function() {
                page.watchEntryUpdates(entry, 1000);

                expect(page._watchedUpdatesPeriodMS).toBe(1000);
                expect(page._watchedEntries[entry.id]).toEqual({
                    entry: entry,
                    periodMS: 1000,
                });
                expect(page._scheduleCheckUpdates).toHaveBeenCalled();
            });

            it('Shorter watch periods take precedent', function() {
                page._watchedUpdatesPeriodMS = 5000;
                page.watchEntryUpdates(entry, 1000);

                expect(page._watchedUpdatesPeriodMS).toBe(1000);
                expect(page._watchedEntries[entry.id]).toEqual({
                    entry: entry,
                    periodMS: 1000,
                });
                expect(page._scheduleCheckUpdates).toHaveBeenCalled();
            });

            it('Subsequent call with longer watch period', function() {
                page._watchedUpdatesPeriodMS = 1000;
                page.watchEntryUpdates(entry, 5000);

                expect(page._watchedUpdatesPeriodMS).toBe(1000);
                expect(page._watchedEntries[entry.id]).toEqual({
                    entry: entry,
                    periodMS: 5000,
                });
                expect(page._scheduleCheckUpdates).toHaveBeenCalled();
            });
        });

        describe('stopWatchingEntryUpdates', function() {
            beforeEach(function() {
                spyOn(page, '_scheduleCheckUpdates');
            });

            it('Switches to next-shortest update period', function() {
                const entry1 = new RB.ReviewRequestPage.Entry({
                    id: '1',
                });

                const entry2 = new RB.ReviewRequestPage.Entry({
                    id: '2',
                });

                page.watchEntryUpdates(entry1, 2000);
                page.watchEntryUpdates(entry2, 1000);
                expect(page._watchedUpdatesPeriodMS).toBe(1000);

                page.stopWatchingEntryUpdates(entry2);
                expect(page._watchedUpdatesPeriodMS).toBe(2000);
            });

            it('Last entry being watched', function() {
                const entry = new RB.ReviewRequestPage.Entry({
                    id: '1',
                });

                page.watchEntryUpdates(entry, 1000);
                page.stopWatchingEntryUpdates(entry);

                expect(_.isEmpty(page._watchedEntries)).toBe(true);
                expect(page._watchedUpdatesTimeout).toBe(null);
                expect(page._watchedUpdatesPeriodMS).toBe(null);
                expect(page._watchedUpdatesLastScheduleTime).toBe(null);
            });
        });
    });

    describe('Dynamic updating', function() {
        it('Scheduled check for update', function() {
            let scheduledCallback = null;

            spyOn(page, '_scheduleCheckUpdates').and.callThrough();
            spyOn(window, 'setTimeout').and.callFake((cb, ms) => {
                scheduledCallback = cb;

                return 'dummy value';
            });
            spyOn(page, '_loadUpdates').and.callThrough();
            spyOn(Backbone, 'sync');

            const entry1 = new RB.ReviewRequestPage.Entry({
                typeID: 'my-entry',
                id: '100',
            });

            const entry2 = new RB.ReviewRequestPage.Entry({
                typeID: 'my-entry',
                id: '200',
            });

            const entry3 = new RB.ReviewRequestPage.Entry({
                typeID: 'another-entry',
                id: 'foo',
            });

            page.watchEntryUpdates(entry1, 2000);
            page.watchEntryUpdates(entry2, 1000);
            page.watchEntryUpdates(entry3, 2000);

            expect(scheduledCallback).not.toBe(null);

            expect(page._scheduleCheckUpdates).toHaveBeenCalled();
            expect(page._watchedUpdatesLastScheduleTime).not.toBe(null);
            expect(page._watchedUpdatesTimeout).not.toBe(null);

            scheduledCallback();

            expect(page._watchedUpdatesLastScheduleTime).not.toBe(null);
            expect(page._watchedUpdatesTimeout).toBe(null);
            expect(page._loadUpdates.calls.count()).toBe(1);
            expect(page._loadUpdates.calls.mostRecent().args[0].entries)
                .toEqual([entry1, entry2, entry3]);

            expect(Backbone.sync.calls.count()).toBe(1);

            const callOptions = Backbone.sync.calls.mostRecent().args[2];
            expect(callOptions.url)
                .toBe('/r/123/_updates/?entries=my-entry:100,200' +
                      ';another-entry:foo');
            expect(callOptions.noActivityIndicator).toBe(true);
            expect(callOptions.dataType).toBe('text');
        });

        describe('Response parsing', function() {
            const TestEntry = RB.ReviewRequestPage.Entry.extend({
                parse(rsp) {
                    return _.extend({
                        myAttr: rsp.myAttr,
                    }, RB.ReviewRequestPage.Entry.prototype.parse.call(this,
                                                                       rsp));
                },
            });

            let entry1;
            let entry2;

            beforeEach(function() {
                spyOn(page, 'trigger').and.callThrough();

                entry1 = new TestEntry({
                    typeID: 'my-entry',
                    id: '1',
                    addedTimestamp: new Date(2017, 7, 1, 0, 0, 0),
                    updatedTimestamp: new Date(2017, 7, 1, 12, 0, 0),
                });

                entry2 = new TestEntry({
                    typeID: 'my-entry',
                    id: '2',
                    addedTimestamp: new Date(2017, 7, 1, 0, 0, 0),
                    updatedTimestamp: new Date(2017, 7, 1, 12, 0, 0),
                });

                page.addEntry(entry1);
                page.addEntry(entry2);
            });

            it('Updates to outdated entries', function() {
                spyOn(entry1, 'beforeApplyUpdate');
                spyOn(entry1, 'afterApplyUpdate');
                spyOn(entry2, 'beforeApplyUpdate');
                spyOn(entry2, 'afterApplyUpdate');

                page._processUpdates([
                    '177\n',
                    '{"type": "entry", "entryType": "my-entry", ',
                    '"entryID": "1", "addedTimestamp": "2017-07-01T00:00:00", ',
                    '"updatedTimestamp": "2017-09-04T14:30:20", ',
                    '"modelData": {"myAttr": "value1"}}',
                    '15\n',
                    '<p>My HTML!</p>',
                    '177\n',
                    '{"type": "entry", "entryType": "my-entry", ',
                    '"entryID": "2", "addedTimestamp": "2017-07-01T00:00:00", ',
                    '"updatedTimestamp": "2017-09-03T14:30:20", ',
                    '"modelData": {"myAttr": "value2"}}',
                    '13\n',
                    '<p>Oh hi!</p>',
                ].join(''));

                /* Check the first entry's updates and events. */
                const metadata1 = {
                    type: 'entry',
                    entryType: 'my-entry',
                    entryID: '1',
                    addedTimestamp: '2017-07-01T00:00:00',
                    updatedTimestamp: '2017-09-04T14:30:20',
                    modelData: {
                        myAttr: 'value1',
                    },
                };
                const html1 = '<p>My HTML!</p>';

                expect(entry1.get('myAttr')).toBe('value1');
                expect(entry1.beforeApplyUpdate)
                    .toHaveBeenCalledWith(metadata1);
                expect(entry1.afterApplyUpdate)
                    .toHaveBeenCalledWith(metadata1);
                expect(page.trigger).toHaveBeenCalledWith(
                    'applyingUpdate:entry', metadata1, html1);
                expect(page.trigger).toHaveBeenCalledWith(
                    'applyingUpdate:entry:1', metadata1, html1);
                expect(page.trigger).toHaveBeenCalledWith(
                    'appliedModelUpdate:entry:1', metadata1, html1);
                expect(page.trigger).toHaveBeenCalledWith(
                    'appliedUpdate:entry:1', metadata1, html1);
                expect(page.trigger).toHaveBeenCalledWith(
                    'appliedUpdate:entry', metadata1, html1);

                /* Check the second entry's updates and events. */
                const metadata2 = {
                    type: 'entry',
                    entryType: 'my-entry',
                    entryID: '2',
                    addedTimestamp: '2017-07-01T00:00:00',
                    updatedTimestamp: '2017-09-03T14:30:20',
                    modelData: {
                        myAttr: 'value2',
                    },
                };
                const html2 = '<p>Oh hi!</p>';

                expect(entry2.get('myAttr')).toBe('value2');
                expect(entry2.beforeApplyUpdate)
                    .toHaveBeenCalledWith(metadata2);
                expect(entry2.afterApplyUpdate)
                    .toHaveBeenCalledWith(metadata2);
                expect(page.trigger).toHaveBeenCalledWith(
                    'applyingUpdate:entry', metadata2, html2);
                expect(page.trigger).toHaveBeenCalledWith(
                    'applyingUpdate:entry:2', metadata2, html2);
                expect(page.trigger).toHaveBeenCalledWith(
                    'appliedModelUpdate:entry:2', metadata2, html2);
                expect(page.trigger).toHaveBeenCalledWith(
                    'appliedUpdate:entry:2', metadata2, html2);
                expect(page.trigger).toHaveBeenCalledWith(
                    'appliedUpdate:entry', metadata2, html2);

                expect(page.trigger).toHaveBeenCalledWith('updatesProcessed');
            });

            it('Updates to up-to-date entries', function() {
                entry1.set('myAttr', 'existing-value');

                spyOn(entry1, 'beforeApplyUpdate');
                spyOn(entry1, 'afterApplyUpdate');

                page._processUpdates([
                    '177\n',
                    '{"type": "entry", "entryType": "my-entry", ',
                    '"entryID": "1", "addedTimestamp": "2016-09-04T14:30:20", ',
                    '"updatedTimestamp": "2016-12-10T12:24:14", ',
                    '"modelData": {"myAttr": "value1"}}',
                    '15\n',
                    '<p>My HTML!</p>',
                ].join(''));

                /* Check the first entry's updates and events. */
                const metadata1 = {
                    type: 'entry',
                    entryType: 'my-entry',
                    entryID: '1',
                    addedTimestamp: '2016-09-04T14:30:20',
                    updatedTimestamp: '2016-09-04T14:30:20',
                    modelData: {
                        myAttr: 'value1',
                    },
                };
                const html1 = '<p>My HTML!</p>';

                expect(entry1.get('myAttr')).toBe('existing-value');
                expect(entry1.beforeApplyUpdate).not.toHaveBeenCalled();
                expect(entry1.afterApplyUpdate).not.toHaveBeenCalled();
                expect(page.trigger).not.toHaveBeenCalledWith(
                    'applyingUpdate:entry', metadata1, html1);
                expect(page.trigger).not.toHaveBeenCalledWith(
                    'applyingUpdate:entry:1', metadata1, html1);
                expect(page.trigger).not.toHaveBeenCalledWith(
                    'appliedModelUpdate:entry:1', metadata1, html1);
                expect(page.trigger).not.toHaveBeenCalledWith(
                    'appliedUpdate:entry:1', metadata1, html1);
                expect(page.trigger).not.toHaveBeenCalledWith(
                    'appliedUpdate:entry', metadata1, html1);

                expect(page.trigger).toHaveBeenCalledWith('updatesProcessed');
            });

            it('Updates to non-entries', function() {
                page._processUpdates([
                    '35\n{"type": "something", "foo": "bar"}',
                    '20\n<div>Something</div>',
                ].join(''));

                const metadata = {
                    type: 'something',
                    foo: 'bar',
                };
                const html = '<div>Something</div>';

                expect(page.trigger).toHaveBeenCalledWith(
                    'applyingUpdate:something', metadata, html);
                expect(page.trigger).toHaveBeenCalledWith(
                    'appliedUpdate:something', metadata, html);

                expect(page.trigger).toHaveBeenCalledWith('updatesProcessed');
            });
        });
    });
});
