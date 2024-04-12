import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
    spyOn,
} from 'jasmine-core';

import {
    PageManager,
    PageView,
} from 'reviewboard/common';


suite('rb/pages/models/PageManager', function() {
    let pageManager: PageManager;
    let page: PageView;

    beforeEach(function() {
        pageManager = new PageManager();
        page = new PageView();

        spyOn(page, 'render');
    });

    describe('Instance', function() {
        let callbacks: {
            cb: (page: PageView) => void;
        };
        let expectedRender: boolean;

        beforeEach(function() {
            expectedRender = false;

            callbacks = {
                cb: (_page: PageView) => {
                    expect(_page).toBe(page);
                    expect(pageManager.get('rendered')).toBe(expectedRender);
                },
            };

            spyOn(callbacks, 'cb');
        });

        describe('Methods', function() {
            describe('beforeReady', function() {
                it('Without page set', function() {
                    pageManager.beforeRender(callbacks.cb);
                    expect(callbacks.cb).not.toHaveBeenCalled();

                    pageManager.set('page', page);
                    expect(callbacks.cb).toHaveBeenCalled();
                });

                it('With page set, not rendered', function() {
                    pageManager.set('page', page);
                    pageManager.set('rendered', false);

                    pageManager.beforeRender(callbacks.cb);
                    expect(callbacks.cb).toHaveBeenCalled();
                });

                it('With page set, rendered', function() {
                    pageManager.set({
                        page: page,
                        rendered: true,
                    });

                    expect(() => pageManager.beforeRender(callbacks.cb))
                        .toThrow();

                    expect(callbacks.cb).not.toHaveBeenCalled();
                });
            });

            describe('ready', function() {
                it('Without page set', function() {
                    pageManager.ready(callbacks.cb);
                    expect(callbacks.cb).not.toHaveBeenCalled();

                    pageManager.set('page', page);
                    expect(pageManager.get('rendered')).toBe(true);
                    expect(page.render).toHaveBeenCalled();

                    expect(callbacks.cb).toHaveBeenCalled();
                });

                it('With page set, not rendered', function() {
                    /* Prevent the page from rendering for this test. */
                    spyOn(pageManager, '_renderPage');

                    pageManager.set('page', page);
                    expect(pageManager.get('rendered')).toBe(false);
                    expect(page.render).not.toHaveBeenCalled();

                    pageManager.ready(callbacks.cb);
                    expect(callbacks.cb).not.toHaveBeenCalled();
                });

                it('With page set, rendered', function() {
                    pageManager.set('page', page);
                    expect(pageManager.get('rendered')).toBe(true);
                    expect(page.render).toHaveBeenCalled();

                    pageManager.ready(callbacks.cb);
                    expect(callbacks.cb).toHaveBeenCalled();
                });
            });
        });
    });

    describe('Class methods', function() {
        let oldInstance: PageManager;

        function cb(page: PageView) { /* Intentionally left blank. */}
        const context = {};

        beforeEach(function() {
            oldInstance = PageManager.instance;
            PageManager.instance = pageManager;
        });

        afterEach(function() {
            PageManager.instance = oldInstance;
        });

        it('beforeRender', function() {
            spyOn(PageManager.instance, 'beforeRender');
            PageManager.beforeRender(cb, context);
            expect(PageManager.instance.beforeRender)
                .toHaveBeenCalledWith(cb, context);
        });

        it('ready', function() {
            spyOn(PageManager.instance, 'ready');
            PageManager.ready(cb, context);
            expect(PageManager.instance.ready)
                .toHaveBeenCalledWith(cb, context);
        });

        it('setPage', function() {
            const page = new PageView();
            PageManager.setPage(page);
            expect(pageManager.get('page')).toBe(page);
        });

        it('getPage', function() {
            const page = new PageView();
            pageManager.set('page', page);
            expect(PageManager.getPage()).toBe(page);
        });
    });
});
