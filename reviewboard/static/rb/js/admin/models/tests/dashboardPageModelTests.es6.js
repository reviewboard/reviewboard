suite('rb/admin/models/DashboardPage', function() {
    let page;

    beforeEach(function() {
        page = new RB.Admin.DashboardPage();
    });

    describe('Widgets', function() {
        it('Loading', function() {
            page.set('widgetsData', [
                {
                    id: 'widget-1',
                    domID: 'widget-1',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                    modelAttrs: {
                        myAttr: 1,
                    },
                    viewOptions: {
                        myOption: true,
                    },
                },
                {
                    id: 'widget-2',
                    domID: 'widget-2',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                    modelAttrs: {
                        myAttr: 2,
                    },
                    viewOptions: {
                        myOption: false,
                    },
                },
            ]);

            const onWidgetLoaded = jasmine.createSpy();

            page.loadWidgets(onWidgetLoaded);

            expect(page.widgets.length).toBe(2);

            const model1 = page.widgets.at(0);
            const model2 = page.widgets.at(1);

            expect(model1).toBeInstanceOf(RB.Admin.Widget);
            expect(model1.get('myAttr')).toBe(1);

            expect(model2).toBeInstanceOf(RB.Admin.Widget);
            expect(model2.get('myAttr')).toBe(2);

            expect(onWidgetLoaded).toHaveBeenCalledTimes(2);
            expect(onWidgetLoaded).toHaveBeenCalledWith({
                domID: 'widget-1',
                ViewType: RB.Admin.WidgetView,
                viewOptions: {
                    myOption: true,
                },
                widgetModel: model1,
            });
            expect(onWidgetLoaded).toHaveBeenCalledWith({
                domID: 'widget-2',
                ViewType: RB.Admin.WidgetView,
                viewOptions: {
                    myOption: false,
                },
                widgetModel: model2,
            });
        });

        it('Loading errors sandboxed', function() {
            spyOn(console, 'error');

            page.set('widgetsData', [
                {
                    id: 'widget-1',
                    domID: 'widget-1',
                    viewClass: 'BadViewClass',
                    modelClass: 'BadModelClass',
                },
                {
                    id: 'widget-2',
                    domID: 'widget-2',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                    modelAttrs: {
                        myAttr: 2,
                    },
                    viewOptions: {
                        myOption: false,
                    },
                },
            ]);

            const onWidgetLoaded = jasmine.createSpy();

            page.loadWidgets(onWidgetLoaded);

            expect(page.widgets.length).toBe(1);

            const model1 = page.widgets.at(0);
            expect(model1).toBeInstanceOf(RB.Admin.Widget);

            expect(onWidgetLoaded).toHaveBeenCalledTimes(1);
            expect(onWidgetLoaded).toHaveBeenCalledWith({
                domID: 'widget-2',
                ViewType: RB.Admin.WidgetView,
                viewOptions: {
                    myOption: false,
                },
                widgetModel: model1,
            });

            expect(console.error).toHaveBeenCalled();
            const args = console.error.calls.argsFor(0);
            expect(args[0]).toBe(
                'Unable to render administration widget "%s": %s');
            expect(args[1]).toBe('widget-1');
        });
    });
});
