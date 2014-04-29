suite('rb/pages/models/PageManager', function() {
    var pageManager,
        page;

    beforeEach(function() {
        pageManager = new RB.PageManager();
        page = new Backbone.View();

        spyOn(page, 'render');
    });

    describe('Instance', function() {
        var callbacks,
            expectedRender;

        beforeEach(function() {
            expectedRender = false;

            callbacks = {
                cb: function(_page) {
                    expect(_page).toBe(page);
                    expect(pageManager.get('rendered')).toBe(expectedRender);
                }
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
                        rendered: true
                    });

                    expect(function() {
                        pageManager.beforeRender(callbacks.cb);
                    }).toThrow();

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
        var oldInstance;

        beforeEach(function() {
            oldInstance = RB.PageManager.instance;
            RB.PageManager.instance = pageManager;
        });

        afterEach(function() {
            RB.PageManager.instance = oldInstance;
        });

        it('beforeRender', function() {
            spyOn(RB.PageManager.instance, 'beforeRender');

            RB.PageManager.beforeRender(1, 2);

            expect(RB.PageManager.instance.beforeRender)
                .toHaveBeenCalledWith(1, 2);
        });

        it('ready', function() {
            spyOn(RB.PageManager.instance, 'ready');

            RB.PageManager.ready(1, 2);

            expect(RB.PageManager.instance.ready)
                .toHaveBeenCalledWith(1, 2);
        });

        it('setPage', function() {
            var page = new Backbone.View();

            RB.PageManager.setPage(page);

            expect(pageManager.get('page')).toBe(page);
        });

        it('getPage', function() {
            var page = new Backbone.View();

            pageManager.set('page', page);

            expect(RB.PageManager.getPage()).toBe(page);
        });
    });
});
