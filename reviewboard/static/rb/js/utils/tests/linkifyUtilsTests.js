describe('utils/linkifyUtils', function() {
    describe('linkifyText', function() {
        describe('URLs', function() {
            it('http-based URLs', function() {
                expect(RB.linkifyText('http://example.com')).toBe(
                       '<a target="_blank" href="http://example.com">' +
                       'http://example.com</a>');
            });

            it('https-based URLs', function() {
                expect(RB.linkifyText('https://example.com')).toBe(
                       '<a target="_blank" href="https://example.com">' +
                       'https://example.com</a>');
            });

            it('Trailing slashes', function() {
                expect(RB.linkifyText('http://example.com/foo/')).toBe(
                       '<a target="_blank" href="http://example.com/foo/">' +
                       'http://example.com/foo/</a>');
            });

            it('Anchors', function() {
                expect(RB.linkifyText('http://example.com/#my-anchor')).toBe(
                       '<a target="_blank" href="' +
                       'http://example.com/#my-anchor">' +
                       'http://example.com/#my-anchor</a>');
            });

            it('Query strings', function() {
                expect(RB.linkifyText('http://example.com/?a=b&c=d')).toBe(
                       '<a target="_blank" href="' +
                       'http://example.com/?a=b&amp;c=d">' +
                       'http://example.com/?a=b&amp;c=d</a>');
            });

            describe('Surrounded by', function() {
                it('(...)', function() {
                    expect(RB.linkifyText('(http://example.com/)')).toBe(
                           '(<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>)');
                });

                it('[...]', function() {
                    expect(RB.linkifyText('[http://example.com/]')).toBe(
                           '[<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>]');
                });

                it('{...}', function() {
                    expect(RB.linkifyText('{http://example.com/}')).toBe(
                           '{<a target="_blank" href="http://example.com/">' +
                           'http://example.com/</a>}');
                });

                it('<...>', function() {
                    expect(RB.linkifyText('<http://example.com/>')).toBe(
                           '&lt;<a target="_blank" href="' +
                           'http://example.com/">http://example.com/</a>&gt;');
                });
            });
        });

        describe('/r/ paths', function() {
            describe('Review requests', function() {
                it('/r/123', function() {
                    expect(RB.linkifyText('/r/123')).toBe(
                        '<a target="_blank" href="/r/123/">/r/123</a>');
                });

                it('/r/123/', function() {
                    expect(RB.linkifyText('/r/123/')).toBe(
                        '<a target="_blank" href="/r/123/">/r/123/</a>');
                });
            });

            describe('Diffs', function() {
                it('/r/123/diff', function() {
                    expect(RB.linkifyText('/r/123/diff')).toBe(
                        '<a target="_blank" href="/r/123/diff/">' +
                        '/r/123/diff</a>');
                });

                it('/r/123/diff/', function() {
                    expect(RB.linkifyText('/r/123/diff/')).toBe(
                        '<a target="_blank" href="/r/123/diff/">' +
                        '/r/123/diff/</a>');
                });
            });
        });

        describe('Surrounded by', function() {
            it('(...)', function() {
                expect(RB.linkifyText('(/r/123/)')).toBe(
                       '(<a target="_blank" href="/r/123/">/r/123/</a>)');
            });

            it('[...]', function() {
                expect(RB.linkifyText('[/r/123/]')).toBe(
                       '[<a target="_blank" href="/r/123/">/r/123/</a>]');
            });

            it('{...}', function() {
                expect(RB.linkifyText('{/r/123/}')).toBe(
                       '{<a target="_blank" href="/r/123/">/r/123/</a>}');
            });

            it('<...>', function() {
                expect(RB.linkifyText('</r/123/>')).toBe(
                       '&lt;<a target="_blank" href="/r/123/">/r/123/</a>&gt;');
            });

            it('text', function() {
                expect(RB.linkifyText('foo/r/123/bar')).toBe('foo/r/123/bar');
            });
        });
    });

    describe('Bug References', function() {
        describe('With bugTrackerURL', function() {
            var bugTrackerURL = 'http://issues/?id=%s';

            it('bug 123', function() {
                expect(RB.linkifyText('bug 123', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'bug 123</a>');
            });

            it('bug #123', function() {
                expect(RB.linkifyText('bug #123', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'bug #123</a>');
            });

            it('issue 123', function() {
                expect(RB.linkifyText('issue 123', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'issue 123</a>');
            });

            it('issue #123', function() {
                expect(RB.linkifyText('issue #123', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=123">' +
                    'issue #123</a>');
            });

            it('bug #abc', function() {
                expect(RB.linkifyText('bug #abc', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=abc">' +
                    'bug #abc</a>');
            });

            it('issue #abc', function() {
                expect(RB.linkifyText('issue #abc', bugTrackerURL)).toBe(
                    '<a target="_blank" href="http://issues/?id=abc">' +
                    'issue #abc</a>');
            });
        });

        describe('Without bugTrackerURL', function() {
            it('bug 123', function() {
                expect(RB.linkifyText('bug 123')).toBe('bug 123');
            });

            it('issue 123', function() {
                expect(RB.linkifyText('issue 123')).toBe('issue 123');
            });
        });
    });
});
