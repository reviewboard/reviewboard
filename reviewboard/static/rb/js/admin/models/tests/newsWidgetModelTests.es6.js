suite('rb/admin/models/NewsWidget', function() {
    let model;

    beforeEach(function() {
        model = new RB.Admin.NewsWidget({
            rssURL: 'http://example.com/news/rss',
        });
    });

    describe('Methods', function() {
        describe('loadNews', function() {
            it('Success', function() {
                function _loadNews(url, options) {
                    expect(url).toBe('http://example.com/news/rss');

                    const payload = dedent`
                        <?xml version="1.0" encoding="utf-8"?>

                        <rss xmlns:atom="http://www.w3.org/2005/Atom"
                             version="2.0">
                         <channel>
                          <title>Channel Name</title>
                          <link>http://example.com/news/</link>
                          <description>Channel description...</description>
                          <atom:link href="http://example.com/news/rss"
                                     rel="self"></atom:link>
                          <language>en-us</language>
                          <lastBuildDate>Sun, 20 Oct 2019 17:26:32 -0700</lastBuildDate>
                          <item>
                           <title>Headline 6</title>
                           <pubDate>Sun, 20 Oct 2019 17:26:32 -0700</pubDate>
                           <link>http://example.com/news/post6</link>
                           <description>Brief summary of 6</description>
                           <author>user1@example.com</author>
                           <guid>http://example.com/news/post6</guid>
                          </item>
                          <item>
                           <title>Headline 5</title>
                           <pubDate>Tue, 01 Oct 2019 13:29:00 -0700</pubDate>
                           <link>http://example.com/news/post5</link>
                           <description>Brief summary of 5</description>
                           <author>user2@example.com</author>
                           <guid>http://example.com/news/post5</guid>
                          </item>
                          <item>
                           <title>Headline 4</title>
                           <pubDate>Thu, 26 Sep 2019 19:29:33 -0700</pubDate>
                           <link>http://example.com/news/post4</link>
                           <description>Brief summary of 4</description>
                           <author>user1@example.com</author>
                           <guid>http://example.com/news/post4</guid>
                          </item>
                          <item>
                           <title>Headline 3</title>
                           <pubDate>Sun, 08 Sep 2019 11:27:05 -0700</pubDate>
                           <link>http://example.com/news/post3</link>
                           <description>Brief summary of 3</description>
                           <author>user2@example.com</author>
                           <guid>http://example.com/news/post3</guid>
                          </item>
                          <item>
                           <title>Headline 2</title>
                           <pubDate>Fri, 30 Aug 2019 23:15:01 -0700</pubDate>
                           <link>http://example.com/news/post2</link>
                           <description>Brief summary of 2</description>
                           <author>user1@example.com</author>
                           <guid>http://example.com/news/post2</guid>
                          </item>
                          <item>
                           <title>Headline 1</title>
                           <pubDate>Thu, 29 Aug 2019 14:30:00 -0700</pubDate>
                           <link>http://example.com/news/post1</link>
                           <description>Brief summary of 1</description>
                           <author>user2@example.com</author>
                           <guid>http://example.com/news/post1</guid>
                          </item>
                         </channel>
                        </rss>
                    `;

                    const parser = new DOMParser();
                    options.success(parser.parseFromString(payload,
                                                           'application/xml'));
                }

                const loadingNewsEventHandler = jasmine.createSpy();

                spyOn($, 'ajax').and.callFake(_loadNews);
                model.on('loadingNews', loadingNewsEventHandler);

                model.loadNews();

                expect(loadingNewsEventHandler).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();

                const newsItems = model.get('newsItems');
                expect(newsItems.length).toBe(5);

                let newsItem = newsItems[0];
                expect(newsItem.date.isSame(Date.UTC(2019, 9, 21, 0, 26, 32)))
                    .toBeTrue();
                expect(newsItem.title).toBe('Headline 6');
                expect(newsItem.url).toBe('http://example.com/news/post6');

                newsItem = newsItems[1];
                expect(newsItem.date.isSame(Date.UTC(2019, 9, 1, 20, 29, 0)))
                    .toBeTrue();
                expect(newsItem.title).toBe('Headline 5');
                expect(newsItem.url).toBe('http://example.com/news/post5');

                newsItem = newsItems[2];
                expect(newsItem.date.isSame(Date.UTC(2019, 8, 27, 2, 29, 33)))
                    .toBeTrue();
                expect(newsItem.title).toBe('Headline 4');
                expect(newsItem.url).toBe('http://example.com/news/post4');

                newsItem = newsItems[3];
                expect(newsItem.date.isSame(Date.UTC(2019, 8, 8, 18, 27, 5)))
                    .toBeTrue();
                expect(newsItem.title).toBe('Headline 3');
                expect(newsItem.url).toBe('http://example.com/news/post3');

                newsItem = newsItems[4];
                expect(newsItem.date.isSame(Date.UTC(2019, 7, 31, 6, 15, 1)))
                    .toBeTrue();
                expect(newsItem.title).toBe('Headline 2');
                expect(newsItem.url).toBe('http://example.com/news/post2');
            });

            it('Error loading feed', function() {
                function _loadNews(url, options) {
                    expect(url).toBe('http://example.com/news/rss');
                    options.error();
                }

                const loadingNewsEventHandler = jasmine.createSpy();

                spyOn($, 'ajax').and.callFake(_loadNews);
                model.on('loadingNews', loadingNewsEventHandler);

                model.loadNews();

                expect(loadingNewsEventHandler).toHaveBeenCalled();
                expect($.ajax).toHaveBeenCalled();

                const newsItems = model.get('newsItems');
                expect(newsItems.length).toBe(0);
            });
        });
    });
});

