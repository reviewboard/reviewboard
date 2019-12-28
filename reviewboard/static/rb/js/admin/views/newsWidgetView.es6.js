/**
 * A widget for displaying news items from an RSS feed.
 */
RB.Admin.NewsWidgetView = RB.Admin.WidgetView.extend({
    canReload: true,
    reloadTitle: gettext('Reload news posts'),

    itemsTemplate: _.template(dedent`
        <% _.each(items, function(item) { %>
         <a href="<%- item.url %>" class="rb-c-admin-news-widget__item"
            target="_blank">
          <span class="rb-c-admin-news-widget__item-date">
           <%- item.date.format('MMM DD') %>
          </span>
          <span class="rb-c-admin-news-widget__item-title">
           <%- item.title %>
          </span>
         </a>
        <% }) %>
    `),

    /**
     * Render the widget.
     *
     * This will set up the actions and begin loading the news.
     */
    renderWidget() {
        const model = this.model;

        this.addFooterAction({
            id: 'more-news',
            el: $('<a href="#" target="_blank">')
                .text(gettext('More News'))
                .attr('href', model.get('newsURL')),
        });

        const subscribeURL = this.model.get('subscribeURL');

        if (subscribeURL) {
            this.addFooterAction({
                id: 'subscribe',
                cssClasses: '-is-right',
                el: $('<a href="#" target="_blank">')
                    .text(gettext('Subscribe'))
                    .attr('href', subscribeURL),
            });
        }

        this.listenTo(model, 'loadingNews',
                      () => this.setReloading(true));
        this.listenTo(model, 'change:newsItems', this._onNewsItemsChanged);

        model.loadNews();
    },

    /**
     * Reload the news posts.
     *
     * This is called in response to a user clicking the Reload action.
     */
    reloadContent() {
        this.model.loadNews();
    },

    /**
     * Handle changes to the list of loaded news items.
     *
     * If the list is empty, this will present an error pointing to the news
     * feed. Otherwise, it will render each of the news items.
     */
    _onNewsItemsChanged() {
        const items = this.model.get('newsItems');

        this.setReloading(false);

        if (items.length > 0) {
            this.$content.html(this.itemsTemplate({
                items: items,
            }));
        } else {
            const $error = $('<p class="rb-c-admin-news-widget__error">')
                .html(interpolate(
                    gettext('There was an error loading the news. Please <a href="%s">visit the news page</a> directly, or try again later.'),
                    [this.model.get('newsURL')]));

            this.$content
                .empty()
                .append($error);
        }

        this.trigger('sizeChanged');
    },
});
