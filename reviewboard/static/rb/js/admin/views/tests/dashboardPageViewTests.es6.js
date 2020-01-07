suite('rb/admin/views/DashboardPageView', function() {
    const pageTemplate = dedent`
        <div>
         <div id="admin-dashboard" style="visibility: hidden">
          <div class="rb-c-admin-widgets">
           <div class="rb-c-admin-widgets__sizer-gutter"></div>
           <div class="rb-c-admin-widgets__sizer-column"></div>
           <div class="rb-c-admin-widgets__main"></div>
          </div>
         </div>
        </div>
    `;

    const widgetTemplate = _.template(dedent`
        <div class="rb-c-admin-widget <%- cssClasses %>" id="<%- domID %>"
         <header class="rb-c-admin-widget__header">
          <h1><%- name %></h1>
          <ul class="rb-c-admin-widget__actions"></ul>
         </header>
         <div class="rb-c-admin-widget__content"></div>
         <footer class="rb-c-admin-widget__footer">
          <ul class="rb-c-admin-widget__actions"></ul>
         </footer>
        </div>
    `);

    let page;
    let pageView;

    beforeEach(function() {
        page = new RB.Admin.DashboardPage();
        pageView = new RB.Admin.DashboardPageView({
            el: $(pageTemplate).appendTo($testsScratch),
            model: page,
        });
    });

    describe('Widgets', function() {
        it('Loading', function() {
            const $main = pageView.$('.rb-c-admin-widgets__main');

            $main.append(
                widgetTemplate({
                    domID: 'widget-1',
                    name: 'Widget 1',
                    cssClasses: '-is-small',
                }),
                widgetTemplate({
                    domID: 'widget-2',
                    name: 'Widget 2',
                    cssClasses: '',
                }),
                widgetTemplate({
                    domID: 'widget-3',
                    name: 'Widget 3',
                    cssClasses: '-is-large',
                }),
                widgetTemplate({
                    domID: 'widget-4',
                    name: 'Widget 4',
                    cssClasses: '-is-small',
                }),
                widgetTemplate({
                    domID: 'widget-5',
                    name: 'Widget 5',
                    cssClasses: '',
                }),
                widgetTemplate({
                    domID: 'widget-6',
                    name: 'Widget 6',
                    cssClasses: '-is-full-size',
                })
            );

            page.set('widgetsData', [
                {
                    id: 'widget-1',
                    domID: 'widget-1',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                },
                {
                    id: 'widget-2',
                    domID: 'widget-2',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                },
                {
                    id: 'widget-3',
                    domID: 'widget-3',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                },
                {
                    id: 'widget-4',
                    domID: 'widget-4',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                },
                {
                    id: 'widget-5',
                    domID: 'widget-5',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                },
                {
                    id: 'widget-6',
                    domID: 'widget-6',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                },
            ]);

            pageView.render();

            const $widgets = pageView._$widgets;
            expect($widgets.length).toBe(6);

            expect($widgets[0].id).toBe('widget-1');
            expect($widgets[1].id).toBe('widget-2');
            expect($widgets[2].id).toBe('widget-3');
            expect($widgets[3].id).toBe('widget-4');
            expect($widgets[4].id).toBe('widget-5');
            expect($widgets[5].id).toBe('widget-6');

            expect($widgets[0]).toHaveClass('js-masonry-item');
            expect($widgets[1]).toHaveClass('js-masonry-item');
            expect($widgets[2]).toHaveClass('js-masonry-item');
            expect($widgets[3]).toHaveClass('js-masonry-item');
            expect($widgets[4]).toHaveClass('js-masonry-item');
            expect($widgets[5]).toHaveClass('js-masonry-item');

            const items = pageView._masonry.items;
            expect(items.length).toBe(6);
            expect(items[0].element).toBe($widgets[5]);
            expect(items[1].element).toBe($widgets[2]);
            expect(items[2].element).toBe($widgets[1]);
            expect(items[3].element).toBe($widgets[4]);
            expect(items[4].element).toBe($widgets[0]);
            expect(items[5].element).toBe($widgets[3]);

            expect(pageView.$el.css('visibility')).toBe('visible');
        });

        describe('sizeChanged event', function() {
            let widgetView;

            beforeEach(function() {
                const $main = pageView.$('.rb-c-admin-widgets__main');

                $main.append(widgetTemplate({
                    domID: 'widget-1',
                    name: 'Widget 1',
                    cssClasses: '',
                }));

                page.set('widgetsData', [{
                    id: 'widget-1',
                    domID: 'widget-1',
                    viewClass: 'RB.Admin.WidgetView',
                    modelClass: 'RB.Admin.Widget',
                }]);

                pageView.render();

                widgetView = pageView._widgetViews['widget-1'];
                expect(widgetView).not.toBeUndefined();

                spyOn(pageView._masonry, 'layout');
            });

            it('Causes re-layout on element size change', function () {
                const $widget = widgetView.$el;

                $widget.width($widget.width() + 100);
                widgetView.trigger('sizeChanged');

                expect(pageView._masonry.layout).toHaveBeenCalled();
            });

            it('Ignored when element size does not change', function () {
                pageView._widgetWidths['widget-1'] = widgetView.$el.width();
                widgetView.trigger('sizeChanged');

                expect(pageView._masonry.layout).not.toHaveBeenCalled();
            });
        });
    });
});
