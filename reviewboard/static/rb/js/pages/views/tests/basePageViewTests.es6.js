suite('rb/pages/views/PageView', function() {
    const pageSidebarTemplate = dedent`
        <div class="rb-c-page-sidebar test-page-sidebar">
         <div class="rb-c-page-sidebar__panes">
          <div class="rb-c-page-sidebar__pane -is-shown">
           <div class="rb-c-page-sidebar__pane-content"></div>
          </div>
         </div>
        </div>
    `;
    let $body;
    let $headerBar;
    let $pageSidebar;
    let $pageContainer;
    let $pageContent;
    let pageView;

    beforeEach(function() {
        $body = $('<div/>').appendTo($testsScratch);
        $headerBar = $('<div/>').appendTo($body);
        $pageContainer = $('<div/>').appendTo($body);
        $pageContent = $('<div/>').appendTo($pageContainer);
        $pageSidebar = $(pageSidebarTemplate).appendTo($body);

        pageView = new RB.PageView({
            $body: $body,
            $headerBar: $headerBar,
            $pageContainer: $pageContainer,
            $pageContent: $pageContent,
            $pageSidebar: $pageSidebar,
        });
    });

    afterEach(function() {
        pageView.remove();
    });

    describe('Rendering', function() {
        it('Default state', function() {
            expect(pageView.isPageRendered).toBe(false);

            pageView.render();

            expect(pageView.hasSidebar).toBe(false);
            expect(pageView.isFullPage).toBe(false);
            expect(pageView.isPageRendered).toBe(true);
            expect(pageView.inMobileMode).toBe(false);
            expect(pageView.headerView).not.toBe(null);
            expect(pageView.$mainSidebar.length).toBe(1);
            expect(pageView.$pageContainer.length).toBe(1);
            expect(pageView.$pageContent.length).toBe(1);
            expect(pageView._$pageSidebar.length).toBe(1);
            expect(pageView._$pageSidebarPanes.length).toBe(1);
            expect(pageView._$mainSidebarPane.length).toBe(1);
        });

        describe('With full-page-content', function() {
            let $mainSidebarPane;

            beforeEach(function() {
                $pageContainer.css('display', 'none');
                $mainSidebarPane = $pageSidebar.find('.-is-shown')
                    .css('display', 'none');
            });

            it('Using body.-is-content-full-page', function() {
                $body.addClass('-is-content-full-page');
                pageView.render();

                expect(pageView.isFullPage).toBe(true);
                expect($mainSidebarPane.css('display')).toBe('block');
                expect($pageContainer.css('display')).toBe('block');
            });

            it('Using legacy body.full-page-content', function() {
                $body.addClass('full-page-content');
                pageView.render();

                expect(pageView.isFullPage).toBe(true);
                expect($mainSidebarPane.css('display')).toBe('block');
                expect($pageContainer.css('display')).toBe('block');
            });
        });

        describe('With sidebar', function() {
            it('Using body.-has-sidebar', function() {
                $body.addClass('-has-sidebar');
                pageView.render();

                expect(pageView.hasSidebar).toBe(true);
            });

            it('Using legacy body.has-sidebar', function() {
                $body.addClass('has-sidebar');
                pageView.render();

                expect(pageView.hasSidebar).toBe(true);
            });
        });
    });

    describe('Drawers', function() {
        beforeEach(function() {
            $body.addClass('-has-sidebar');
        });

        describe('Setting drawer', function() {
            it('In mobile mode', function() {
                pageView.render();
                pageView.inMobileMode = true;
                pageView.setDrawer(new RB.DrawerView());

                expect($body.children('.rb-c-drawer').length).toBe(1);
            });

            it('In desktop mode', function() {
                pageView.render();
                pageView.inMobileMode = false;
                pageView.setDrawer(new RB.DrawerView());

                const $panes = $pageSidebar.children(
                    '.rb-c-page-sidebar__panes');

                expect($panes.children('.rb-c-drawer').length).toBe(1);
            });
        });

        describe('State changes', function() {
            let drawer;

            beforeEach(function() {
                drawer = new RB.DrawerView();
                pageView.render();

                spyOn(pageView, '_updateSize');
                pageView.setDrawer(drawer);

                expect(pageView._updateSize).not.toHaveBeenCalled();
            });

            it('Showing', function() {
                drawer.show();
                expect(pageView._updateSize).toHaveBeenCalled();
            });

            it('Hiding', function() {
                drawer.show();
                expect(pageView._updateSize).toHaveBeenCalled();
            });
        });
    });

    describe('Events', function() {
        describe('mobileModeChanged', function() {
            let eventHandler;

            beforeEach(function() {
                eventHandler = jasmine.createSpy('handler');

                pageView.render();
                pageView.on('inMobileModeChanged', eventHandler);

                spyOn(pageView, '_updateSize');
                spyOn(pageView, 'onMobileModeChanged');
            });

            it('To mobile mode', function() {
                pageView.inMobileMode = false;
                pageView.headerView.trigger('mobileModeChanged', true);

                expect(pageView.inMobileMode).toBe(true);
                expect(pageView._updateSize).toHaveBeenCalled();
                expect(pageView.onMobileModeChanged)
                    .toHaveBeenCalledWith(true);
                expect(eventHandler).toHaveBeenCalledWith(true);
            });

            it('To desktop mode', function() {
                pageView.inMobileMode = true;
                pageView.headerView.trigger('mobileModeChanged', false);

                expect(pageView.inMobileMode).toBe(false);
                expect(pageView._updateSize).toHaveBeenCalled();
                expect(pageView.onMobileModeChanged)
                    .toHaveBeenCalledWith(false);
                expect(eventHandler).toHaveBeenCalledWith(false);
            });
        });

        describe('resize', function() {
            beforeEach(function() {
                pageView.render();

                spyOn(pageView, '_updateSize').and.callThrough();
                spyOn(pageView, 'onResize');

                /* Force some heights and offsets. */
                $pageContainer.css('height', 'auto');
                $pageSidebar.css('height', 'auto');

                spyOn(pageView.$window, 'height').and.callFake(() => 1000);
                spyOn($pageContainer, 'offset').and.callFake(() => ({
                    top: 20,
                    left: 0,
                }));
                spyOn($pageSidebar, 'offset').and.callFake(() => ({
                    top: 10,
                    left: 0,
                }));
            });

            describe('In mobile mode', function() {
                beforeEach(function() {
                    pageView.inMobileMode = true;
                });

                it('Default state', function() {
                    pageView.$window.triggerHandler('resize');

                    expect(pageView._updateSize).toHaveBeenCalled();
                    expect($pageContainer[0].style.height).toBe('');
                    expect($pageSidebar[0].style.height).toBe('');

                    expect(pageView.onResize).toHaveBeenCalled();
                });

                describe('In full-page content mode', function() {
                    let drawer;

                    beforeEach(function() {
                        pageView.isFullPage = true;

                        drawer = new RB.DrawerView();

                        /*
                         * We're probably not running tests in actual mobile
                         * mode, so the stylesheet setting a minimum height on
                         * the drawer won't take effect. Instead, force one.
                         */
                        drawer.$el.outerHeight(300);
                    });

                    it('Without drawer', function() {
                        pageView.$window.triggerHandler('resize');

                        expect(pageView._updateSize).toHaveBeenCalled();
                        expect($pageContainer[0].style.height).toBe('980px');
                        expect($pageSidebar[0].style.height).toBe('');

                        expect(pageView.onResize).toHaveBeenCalled();
                    });

                    it('With open drawer', function() {
                        pageView.hasSidebar = true;
                        pageView.setDrawer(drawer);

                        drawer.show();
                        pageView.$window.triggerHandler('resize');

                        expect(pageView._updateSize).toHaveBeenCalled();
                        expect($pageContainer[0].style.height).toBe('680px');
                        expect($pageSidebar[0].style.height).toBe('');

                        expect(pageView.onResize).toHaveBeenCalled();
                    });

                    it('With closed drawer', function() {
                        pageView.hasSidebar = true;
                        pageView.setDrawer(drawer);

                        pageView.$window.triggerHandler('resize');

                        expect(pageView._updateSize).toHaveBeenCalled();
                        expect($pageContainer[0].style.height).toBe('980px');
                        expect($pageSidebar[0].style.height).toBe('');

                        expect(pageView.onResize).toHaveBeenCalled();
                    });
                });
            });

            describe('In desktop mode', function() {
                beforeEach(function() {
                    pageView.inMobileMode = false;
                });

                it('Default state', function() {
                    pageView.$window.triggerHandler('resize');

                    expect(pageView._updateSize).toHaveBeenCalled();
                    expect($pageContainer[0].style.height).toBe('');
                    expect($pageSidebar[0].style.height).toBe('');

                    expect(pageView.onResize).toHaveBeenCalled();
                });

                it('In full-page content mode', function() {
                    pageView.isFullPage = true;

                    pageView.$window.triggerHandler('resize');

                    expect(pageView._updateSize).toHaveBeenCalled();
                    expect($pageContainer[0].style.height).toBe('980px');
                    expect($pageSidebar[0].style.height).toBe('990px');

                    expect(pageView.onResize).toHaveBeenCalled();
                });
            });
        });
    });
});
