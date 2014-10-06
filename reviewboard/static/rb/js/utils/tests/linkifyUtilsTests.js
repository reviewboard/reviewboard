suite('rb/utils/linkifyUtils', function() {
    var bugTrackerURL = 'http://issues/?id=%s';

    describe('linkifyChildren', function() {
        it('URLs', function() {
            var $el = $('<p><span>http://example.com</span></p>');

            RB.LinkifyUtils.linkifyChildren($el[0]);

            expect($el.html()).toBe(
                '<span><a target="_blank" href="http://example.com">' +
                'http://example.com</a></span>');
        });

        it('Bugs', function() {
            var $el = $('<p><span>Bug #123</span></p>');

            RB.LinkifyUtils.linkifyChildren($el[0], bugTrackerURL);

            expect($el.html()).toBe(
                '<span><a target="_blank" href="http://issues/?id=123">' +
                'Bug #123</a></span>');
        });

        it('/r/ paths', function() {
            var $el = $('<p><span>/r/123/</span></p>');

            RB.LinkifyUtils.linkifyChildren($el[0]);

            expect($el.html()).toBe(
                '<span><a target="_blank" href="/r/123/">' +
                '/r/123/</a></span>');
        });

        it('Skips <a> elements', function() {
            var $el = $('<p><span><a href="http://example.com">/r/123</a>' +
                        '</span></p>');

            RB.LinkifyUtils.linkifyChildren($el[0]);

            expect($el.html()).toBe(
                '<span><a href="http://example.com">/r/123</a></span>');
        });

        it('Skips <pre> elements', function() {
            var $el = $('<div><pre>/r/123</pre></div>');

            RB.LinkifyUtils.linkifyChildren($el[0]);

            expect($el.html()).toBe('<pre>/r/123</pre>');
        });
    });

    describe('linkifyText', function() {
        describe('URLs', function() {
            it('http-based URLs', function() {
                expect(RB.LinkifyUtils.linkifyText('http://example.com')).toBe(
                       '<a target="_blank" href="http://example.com">' +
                       'http://example.com</a>');
            });

            it('https-based URLs', function() {
                expect(RB.LinkifyUtils.linkifyText('https://example.com')).toBe(
                       '<a target="_blank" href="https://example.com">' +
                       'https://example.com</a>');
            });

            it('Trailing slashes', function() {
                expect(RB.LinkifyUtils.linkifyText('http://example.com/foo/')).toBe(
                       '<a target="_blank" href="http://example.com/foo/">' +
                       'http://example.com/foo/</a>');
            });

            it('Anchors', function() {
                expect(RB.LinkifyUtils.linkifyText('http://example.com/#my-anchor')).toBe(
                       '<a target="_blank" href="' +
                       'http://example.com/#my-anchor">' +
                       'http://example.com/#my-anchor</a>');
            });

            it('Query strings', function() {
                expect(RB.LinkifyUtils.linkifyText('http://example.com/?a=b&c=d')).toBe(
                       '<a target="_blank" href="' +
                       'http://example.com/?a=b&amp;c=d">' +
                       'http://example.com/?a=b&amp;c=d</a>');
            });

            describe('Surrounded by', function() {
                it('(...)', function() {
                    expect(RB.LinkifyUtils.linkifyText('(http://example.com/)')).toBe(
                           '(<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>)');
                });

                it('[...]', function() {
                    expect(RB.LinkifyUtils.linkifyText('[http://example.com/]')).toBe(
                           '[<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>]');
                });

                it('{...}', function() {
                    expect(RB.LinkifyUtils.linkifyText('{http://example.com/}')).toBe(
                           '{<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>}');
                });

                it('<...>', function() {
                    expect(RB.LinkifyUtils.linkifyText('<http://example.com/>')).toBe(
                           '&lt;<a target="_blank" href="' +
                           'http://example.com/">http://example.com/</a>&gt;');
                });
            });
        });

        describe('/r/ paths', function() {
            describe('Review requests', function() {
                it('/r/123', function() {
                    expect(RB.LinkifyUtils.linkifyText('/r/123')).toBe(
                        '<a target="_blank" href="/r/123/">/r/123</a>');
                });

                it('/r/123/', function() {
                    expect(RB.LinkifyUtils.linkifyText('/r/123/')).toBe(
                        '<a target="_blank" href="/r/123/">/r/123/</a>');
                });

                it('/r/123/ in MD format', function() {
                    expect(RB.LinkifyUtils.linkifyReviewRequests('/r/123/', true)).toBe(
                        '[/r/123/](/r/123/)');
                });
            });

            describe('Diffs', function() {
                it('/r/123/diff', function() {
                    expect(RB.LinkifyUtils.linkifyText('/r/123/diff')).toBe(
                        '<a target="_blank" href="/r/123/diff/">' +
                        '/r/123/diff</a>');
                });

                it('/r/123/diff/', function() {
                    expect(RB.LinkifyUtils.linkifyText('/r/123/diff/')).toBe(
                        '<a target="_blank" href="/r/123/diff/">' +
                        '/r/123/diff/</a>');
                });

                it('/r/123/diff/ in MD format', function() {
                    expect(RB.LinkifyUtils.linkifyReviewRequests('/r/123/diff/', true)).toBe(
                        '[/r/123/diff/](/r/123/diff/)');
                });
            });
        });

        describe('Surrounded by', function() {
            it('(...)', function() {
                expect(RB.LinkifyUtils.linkifyText('(/r/123/)')).toBe(
                       '(<a target="_blank" href="/r/123/">/r/123/</a>)');
            });

            it('[...]', function() {
                expect(RB.LinkifyUtils.linkifyText('[/r/123/]')).toBe(
                       '[<a target="_blank" href="/r/123/">/r/123/</a>]');
            });

            it('{...}', function() {
                expect(RB.LinkifyUtils.linkifyText('{/r/123/}')).toBe(
                       '{<a target="_blank" href="/r/123/">/r/123/</a>}');
            });

            it('<...>', function() {
                expect(RB.LinkifyUtils.linkifyText('</r/123/>')).toBe(
                       '&lt;<a target="_blank" href="/r/123/">/r/123/</a>&gt;');
            });

            it('text', function() {
                expect(RB.LinkifyUtils.linkifyText('foo/r/123/bar')).toBe('foo/r/123/bar');
            });
        });
    });

    describe('Bug References', function() {
        describe('With bugTrackerURL', function() {
            it('bug 123', function() {
                expect(RB.LinkifyUtils.linkifyText('bug 123', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'bug 123</a>');
            });

            it('bug #123', function() {
                expect(RB.LinkifyUtils.linkifyText('bug #123', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'bug #123</a>');
            });

            it('issue 123', function() {
                expect(RB.LinkifyUtils.linkifyText('issue 123', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'issue 123</a>');
            });

            it('issue #123', function() {
                expect(RB.LinkifyUtils.linkifyText('issue #123', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'issue #123</a>');
            });

            it('bug #abc', function() {
                expect(RB.LinkifyUtils.linkifyText('bug #abc', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=abc">' +
                    'bug #abc</a>');
            });

            it('issue #abc', function() {
                expect(RB.LinkifyUtils.linkifyText('issue #abc', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=abc">' +
                    'issue #abc</a>');
            });

            it('issue #abc, issue 2', function() {
                expect(RB.LinkifyUtils.linkifyText('issue #abc, issue 2', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=abc">' +
                    'issue #abc</a>, <a target="_blank" ' +
                    'href="http://issues/?id=2">issue 2</a>');
            });

            it('issue #abc in MD format', function() {
                expect(RB.LinkifyUtils.linkifyBugs('issue #abc', bugTrackerURL, true)).toBe(
                    '[issue #abc](http://issues/?id=abc)');
            });
        });

        describe('Without bugTrackerURL', function() {
            it('bug 123', function() {
                expect(RB.LinkifyUtils.linkifyText('bug 123')).toBe('bug 123');
            });

            it('issue 123', function() {
                expect(RB.LinkifyUtils.linkifyText('issue 123')).toBe('issue 123');
            });
        });
    });
});
