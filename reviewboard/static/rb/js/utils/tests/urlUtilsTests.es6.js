suite('rb/utils/urlUtils', function() {
    describe('getLocationHash', function() {
        beforeEach(function() {
            window.xss = function() {};
        });

        afterEach(function() {
            if (window.hasOwnProperty('xss')) {
                delete window.xss;
            }
        });

        it('Prevents XSS injection', function(done) {
            spyOn(window, 'xss');

            const url = 'http://www.example.com/#<img/src/onerror=window.xss()>';
            const hash = RB.getLocationHash(url);

            $(`a[name="${hash}"]`);

            _.delay(function() {
                expect(window.xss).not.toHaveBeenCalled();
                done();
            });
        });
    });
});
