suite('rb/utils/urlUtils', function() {
    describe('getLocationHash', function() {
        var url = 'http://www.example.com/#<img/src/onerror=window.xss()>',
            hash = RB.getLocationHash(url),
            done;

        beforeEach(function() {
            done = false;
            window.xss = function() {};
        });

        afterEach(function() {
            if (window.hasOwnProperty('xss')) {
                delete window.xss;
            }
        });

        it('Prevents XSS injection', function(done) {
            spyOn(window, 'xss');

            $('a[name="' + hash + '"]');

            _.delay(function() {
                expect(window.xss).not.toHaveBeenCalled();
                done();
            });
        });
    });
});
