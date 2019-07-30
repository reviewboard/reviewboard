suite('rb/utils/linkifyUtils', function() {
    var bugTrackerURL = 'http://issues/?id=--bug_id--';

    describe('linkifyChildren', function() {
        it('URLs', function() {
            var $el = $('<p><span>http://example.com</span></p>');

            RB.LinkifyUtils.linkifyChildren($el[0]);

            const $span = $el.children('span');
            expect($span.length).toBe(1);

            const $a = $span.children('a');
            expect($a.length).toBe(1);
            expect($a.attr('target')).toBe('_blank');
            expect($a.attr('href')).toBe('http://example.com');
            expect($a.text()).toBe('http://example.com');
        });

        it('Bugs', function() {
            var $el = $('<p><span>Bug #123</span></p>');

            RB.LinkifyUtils.linkifyChildren($el[0], bugTrackerURL);

            const $span = $el.children('span');
            expect($span.length).toBe(1);

            const $a = $span.children('a');
            expect($a.length).toBe(1);
            expect($a.attr('target')).toBe('_blank');
            expect($a.attr('href')).toBe('http://issues/?id=123');
            expect($a.text()).toBe('Bug #123');
        });

        it('/r/ paths', function() {
            var $el = $('<p><span>/r/123/</span></p>');

            RB.LinkifyUtils.linkifyChildren($el[0]);

            const $span = $el.children('span');
            expect($span.length).toBe(1);

            const $a = $span.children('a');
            expect($a.length).toBe(1);
            expect($a.attr('target')).toBe('_blank');
            expect($a.attr('href')).toBe('/r/123/');
            expect($a.attr('class')).toBe('review-request-link');
            expect($a.text()).toBe('/r/123/');
        });

        it('Skips <a> elements', function() {
            var $el = $('<p><span><a href="http://example.com">/r/123</a>' +
                        '</span></p>');

            RB.LinkifyUtils.linkifyChildren($el[0]);

            const $span = $el.children('span');
            expect($span.length).toBe(1);

            const $a = $span.children('a');
            expect($a.length).toBe(1);
            expect($a.attr('target')).toBe(undefined);
            expect($a.attr('href')).toBe('http://example.com');
            expect($a.text()).toBe('/r/123');
        });

        it('Skips <pre> elements', function() {
            var $el = $('<div><pre>/r/123</pre></div>');

            RB.LinkifyUtils.linkifyChildren($el[0]);

            expect($el.html()).toBe('<pre>/r/123</pre>');
        });
    });

    describe('linkifyText', function() {
        describe('URLs', function() {
            const linkifyText = RB.LinkifyUtils.linkifyText;

            it('http://', function() {
                expect(linkifyText('http://example.com')).toBe(
                       '<a target="_blank" href="http://example.com">' +
                       'http://example.com</a>');
            });

            it('https://', function() {
                expect(linkifyText('https://example.com')).toBe(
                       '<a target="_blank" href="https://example.com">' +
                       'https://example.com</a>');
            });

            it('ftp://', function() {
                expect(linkifyText('ftp://example.com')).toBe(
                       '<a target="_blank" href="ftp://example.com">' +
                       'ftp://example.com</a>');
            });

            it('ftps://', function() {
                expect(linkifyText('ftps://example.com')).toBe(
                       '<a target="_blank" href="ftps://example.com">' +
                       'ftps://example.com</a>');
            });

            it('gopher://', function() {
                expect(linkifyText('gopher://example.com')).toBe(
                       '<a target="_blank" href="gopher://example.com">' +
                       'gopher://example.com</a>');
            });

            it('mailto:', function() {
                expect(linkifyText('mailto:user@example.com')).toBe(
                       '<a target="_blank" href="mailto:user@example.com">' +
                       'mailto:user@example.com</a>');
            });

            it('news:', function() {
                expect(linkifyText('news:example.com'))
                    .toBe('<a target="_blank" href="news:example.com">' +
                          'news:example.com</a>');
            });

            it('sms:', function() {
                expect(linkifyText('sms:example.com'))
                    .toBe('<a target="_blank" href="sms:example.com">' +
                          'sms:example.com</a>');
            });

            it('javascript: (unlinked)', function() {
                expect(linkifyText('javascript:test'))
                    .toBe('javascript:test');
            });

            it('javascript:// (unlinked)', function() {
                expect(linkifyText('javascript://test'))
                    .toBe('javascript://test');
            });

            it('Trailing slashes', function() {
                expect(linkifyText('http://example.com/foo/')).toBe(
                       '<a target="_blank" href="http://example.com/foo/">' +
                       'http://example.com/foo/</a>');
            });

            it('Anchors', function() {
                expect(linkifyText('http://example.com/#my-anchor')).toBe(
                       '<a target="_blank" href="' +
                       'http://example.com/#my-anchor">' +
                       'http://example.com/#my-anchor</a>');
            });

            it('Query strings', function() {
                expect(linkifyText('http://example.com/?a=b&c=d')).toBe(
                       '<a target="_blank" href="' +
                       'http://example.com/?a=b&amp;c=d">' +
                       'http://example.com/?a=b&amp;c=d</a>');
            });

            describe('Surrounded by', function() {
                it('(...)', function() {
                    expect(linkifyText('(http://example.com/)')).toBe(
                           '(<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>)');
                });

                it('[...]', function() {
                    expect(linkifyText('[http://example.com/]')).toBe(
                           '[<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>]');
                });

                it('{...}', function() {
                    expect(linkifyText('{http://example.com/}')).toBe(
                           '{<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>}');
                });

                it('<...>', function() {
                    expect(linkifyText('<http://example.com/>')).toBe(
                           '&lt;<a target="_blank" href="' +
                           'http://example.com/">http://example.com/</a>&gt;');
                });
            });
        });

        describe('/r/ paths', function() {
            describe('Review requests', function() {
                it('/r/123', function() {
                    expect(RB.LinkifyUtils.linkifyText('/r/123')).toBe(
                        '<a target="_blank" href="/r/123/" ' +
                        'class="review-request-link">/r/123</a>');
                });

                it('/r/123/', function() {
                    expect(RB.LinkifyUtils.linkifyText('/r/123/')).toBe(
                        '<a target="_blank" href="/r/123/" ' +
                        'class="review-request-link">/r/123/</a>');
                });
            });

            describe('Diffs', function() {
                it('/r/123/diff', function() {
                    expect(RB.LinkifyUtils.linkifyText('/r/123/diff')).toBe(
                        '<a target="_blank" href="/r/123/diff/" ' +
                        'class="review-request-link">/r/123/diff</a>');
                });

                it('/r/123/diff/', function() {
                    expect(RB.LinkifyUtils.linkifyText('/r/123/diff/')).toBe(
                        '<a target="_blank" href="/r/123/diff/" ' +
                        'class="review-request-link">/r/123/diff/</a>');
                });
            });
        });

        describe('Surrounded by', function() {
            it('(...)', function() {
                expect(RB.LinkifyUtils.linkifyText('(/r/123/)')).toBe(
                       '(<a target="_blank" href="/r/123/" ' +
                       'class="review-request-link">/r/123/</a>)');
            });

            it('[...]', function() {
                expect(RB.LinkifyUtils.linkifyText('[/r/123/]')).toBe(
                       '[<a target="_blank" href="/r/123/" ' +
                       'class="review-request-link">/r/123/</a>]');
            });

            it('{...}', function() {
                expect(RB.LinkifyUtils.linkifyText('{/r/123/}')).toBe(
                       '{<a target="_blank" href="/r/123/" ' +
                       'class="review-request-link">/r/123/</a>}');
            });

            it('<...>', function() {
                expect(RB.LinkifyUtils.linkifyText('</r/123/>')).toBe(
                       '&lt;<a target="_blank" href="/r/123/" ' +
                       'class="review-request-link">/r/123/</a>&gt;');
            });

            it('text', function() {
                expect(RB.LinkifyUtils.linkifyText('foo/r/123/bar')).toBe(
                       'foo/r/123/bar');
            });
        });
    });

    describe('Bug References', function() {
        describe('With bugTrackerURL', function() {
            function linkifyText(text) {
                return RB.LinkifyUtils.linkifyText(text, bugTrackerURL);
            }

            it('bug 123', function() {
                expect(linkifyText('bug 123')).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'bug 123</a>');
            });

            it('bug #123', function() {
                expect(linkifyText('bug #123')).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'bug #123</a>');
            });

            it('issue 123', function() {
                expect(linkifyText('issue 123')).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'issue 123</a>');
            });

            it('issue #123', function() {
                expect(linkifyText('issue #123')).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'issue #123</a>');
            });

            it('bug #abc', function() {
                expect(linkifyText('bug #abc')).toBe(
                    '<a target="_blank" href="http://issues/?id=abc">' +
                    'bug #abc</a>');
            });

            it('issue #abc', function() {
                expect(linkifyText('issue #abc')).toBe(
                    '<a target="_blank" href="http://issues/?id=abc">' +
                    'issue #abc</a>');
            });

            it('issue #abc, issue 2', function() {
                expect(linkifyText('issue #abc, issue 2')).toBe(
                    '<a target="_blank" href="http://issues/?id=abc">' +
                    'issue #abc</a>, <a target="_blank" ' +
                    'href="http://issues/?id=2">issue 2</a>');
            });

            it('(issue #abc-123) [bug #cba-321]', function() {
                expect(linkifyText('(issue #abc-123) [bug #cba-321]')).toBe(
                    '(<a target="_blank" href="http://issues/?id=abc-123">' +
                    'issue #abc-123</a>) [<a target="_blank" ' +
                    'href="http://issues/?id=cba-321">bug #cba-321</a>]');
            });
        });

        describe('Without bugTrackerURL', function() {
            const linkifyText = RB.LinkifyUtils.linkifyText;

            it('bug 123', function() {
                expect(linkifyText('bug 123')).toBe('bug 123');
            });

            it('issue 123', function() {
                expect(linkifyText('issue 123')).toBe('issue 123');
            });
        });
    });
});
