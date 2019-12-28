suite('rb/admin/views/NewsWidgetView', function() {
    const template = dedent`
        <div class="rb-c-admin-widget rb-c-news-admin-widget">
         <header class="rb-c-admin-widget__header">
          <ul class="rb-c-admin-widget__actions"></ul>
         </header>
         <div class="rb-c-admin-widget__content"></div>
         <footer class="rb-c-admin-widget__footer">
          <ul class="rb-c-admin-widget__actions"></ul>
         </footer>
        </div>
    `;

    let model;
    let view;

    beforeEach(function() {
        model = new RB.Admin.NewsWidget({
            newsURL: 'http://example.com/news/',
        });

        view = new RB.Admin.NewsWidgetView({
            el: $(template),
            model: model,
        });

        spyOn(model, 'loadNews');
    });

    describe('Rendering', function() {
        describe('Actions', function() {
            it('More News', function() {
                view.render();

                const $actions = view.$footerActions.children();
                expect($actions.length).toBe(1);

                const $action = $actions.eq(0);
                expect($action.hasClass('js-action-more-news')).toBeTrue();
                expect($action.children('a').attr('href'))
                    .toBe('http://example.com/news/');
            });

            it('Subscribe', function() {
                model.set('subscribeURL', 'http://example.com/news/subscribe/');
                view.render();

                const $actions = view.$footerActions.children();
                expect($actions.length).toBe(2);

                const $action = $actions.eq(1);
                expect($action.hasClass('js-action-subscribe')).toBeTrue();
                expect($action.children('a').attr('href'))
                    .toBe('http://example.com/news/subscribe/');
            });

            describe('Reload', function() {
                it('On loadingNews event', function() {
                    view.render();

                    const $action = view.$headerActions.children(
                        '.js-action-reload');
                    expect($action.hasClass('fa-spin')).toBeFalse();

                    model.trigger('loadingNews');
                    expect($action.hasClass('fa-spin')).toBeTrue();
                });

                it('On change:newsItems event', function() {
                    view.render();

                    const $action = view.$headerActions.children(
                        '.js-action-reload');

                    view.setReloading(true);
                    expect($action.hasClass('fa-spin')).toBeTrue();

                    model.set('newsItems', []);
                    expect($action.hasClass('fa-spin')).toBeFalse();
                });
            });
        });

        it('News items', function() {
            view.render();

            model.set('newsItems', [
                {
                    date: moment(Date.UTC(2019, 9, 21, 0, 26, 32)),
                    title: 'Headline 6',
                    url: 'http://example.com/news/post6',
                },
                {
                    date: moment(Date.UTC(2019, 9, 1, 20, 29, 0)),
                    title: 'Headline 5',
                    url: 'http://example.com/news/post5',
                },
                {
                    date: moment(Date.UTC(2019, 8, 27, 2, 29, 33)),
                    title: 'Headline 4',
                    url: 'http://example.com/news/post4',
                },
            ]);

            const $items = view.$content.children();
            expect($items.length).toBe(3);

            let $item = $items.eq(0);
            expect($item.attr('href')).toBe('http://example.com/news/post6');
            expect(
                $item.find('.rb-c-admin-news-widget__item-date').text().strip()
            ).toBe('Oct 20');
            expect(
                $item.find('.rb-c-admin-news-widget__item-title').text().strip()
            ).toBe('Headline 6');

            $item = $items.eq(1);
            expect($item.attr('href')).toBe('http://example.com/news/post5');
            expect(
                $item.find('.rb-c-admin-news-widget__item-date')
                .text().strip()
            ).toBe('Oct 01');
            expect(
                $item.find('.rb-c-admin-news-widget__item-title')
                .text().strip()
            ).toBe('Headline 5');

            $item = $items.eq(2);
            expect($item.attr('href')).toBe('http://example.com/news/post4');
            expect(
                $item.find('.rb-c-admin-news-widget__item-date')
                .text().strip()
            ).toBe('Sep 26');
            expect(
                $item.find('.rb-c-admin-news-widget__item-title')
                .text().strip()
            ).toBe('Headline 4');
        });

        it('Load errors', function() {
            view.render();

            model.set('newsItems', []);

            const $els = view.$content.children();
            expect($els.length).toBe(1);

            const $error = $els.eq(0);
            expect($error.hasClass('rb-c-admin-news-widget__error'))
                .toBeTrue();
            expect($error.html().strip()).toBe(
                'There was an error loading the news. Please ' +
                '<a href="http://example.com/news/">visit the news page</a> ' +
                'directly, or try again later.');
        });
    });
});
