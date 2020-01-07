/**
 * State and operations for the administration UI's news widget.
 *
 * Model Attributes:
 *     maxItems (number):
 *         The maximum number of items to parse from the feed.
 *
 *     newsItems (Array of object):
 *         The list of news items to render. Each entry represents a news item,
 *         and is an object with the following keys:
 *
 *         ``date`` (:js:class:`Moment`):
 *             The parsed date.
 *
 *          ``title`` (string):
 *              The title of the news entry.
 *
 *          ``url`` (string):
 *              The URL to the news page for the item.
 *
 *     newsURL (string):
 *         The URL to the news page, for linking in the browser.
 *
 *     rssURL (string):
 *         The URL to the news RSS feed.
 *
 *     subscribeURL (string):
 *         The URL to a subscription page for the news feed or newsletter.
 */
RB.Admin.NewsWidget = RB.Admin.Widget.extend({
    defaults: _.defaults({
        maxItems: 5,
        newsItems: null,
        newsURL: null,
        rssURL: null,
        subscribeURL: null,
    }, RB.Admin.Widget.prototype.defaults),

    /**
     * Load the latest news from the server.
     *
     * This will attempt to load the news feed and populate the ``newsItems``
     * attribute with the results. If there's an error when loading,
     * ``newsItems`` will be set to an empty array.
     *
     * Before attempting to load the news, this will trigger the
     * ``loadingNews`` event.
     */
    loadNews() {
        this.trigger('loadingNews');

        $.ajax(this.get('rssURL'), {
            accepts: {
                xml: 'application/rss+xml',
            },
            dataType: 'xml',
            success: data => {
                const maxItems = this.get('maxItems');
                const $items = $(data).find(`item:lt(${maxItems})`);

                this.set('newsItems', _.map($items, item => {
                    const $item = $(item);

                    return {
                        date: moment($item.find('pubDate').text(),
                                     'ddd, DD MMM YYYY HH:mm:ss ZZ'),
                        title: $item.find('title').text(),
                        url: $item.find('link').text(),
                    };
                }));
            },
            error: () => {
                this.set('newsItems', []);
            },
        });
    },
});
