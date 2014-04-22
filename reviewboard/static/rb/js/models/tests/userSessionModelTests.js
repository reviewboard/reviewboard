suite('rb/models/UserSession', function() {
    describe('create', function() {
        it('Instance is set', function() {
            var session;

            RB.UserSession.instance = null;
            session = RB.UserSession.create({
                username: 'testuser'
            });

            expect(session).toBe(RB.UserSession.instance);
        });

        it('Second attempt fails', function() {
            RB.UserSession.instance = null;
            RB.UserSession.create({
                username: 'testuser'
            });

            expect(console.assert).toHaveBeenCalled();
            expect(console.assert.calls[0].args[0]).toBeTruthy();

            expect(function() {
                RB.UserSession.create({
                    username: 'foo'
                });
            }).toThrow();

            expect(console.assert).toHaveBeenCalled();
            expect(console.assert.calls[1].args[0]).toBeFalsy();
        });
    });

    describe('Attributes', function() {
        var session;

        beforeEach(function() {
            session = RB.UserSession.instance;
        });

        describe('diffsShowExtraWhitespace', function() {
            describe('Loads from cookie', function() {
                it('When "true"', function() {
                    spyOn($, 'cookie').andReturn('true');

                    RB.UserSession.instance = null;
                    session = RB.UserSession.create({
                        username: 'testuser'
                    });

                    expect($.cookie).toHaveBeenCalledWith('show_ew');
                    expect(session.get('diffsShowExtraWhitespace')).toBe(true);
                });

                it('When "false"', function() {
                    spyOn($, 'cookie').andReturn('false');

                    RB.UserSession.instance = null;
                    session = RB.UserSession.create({
                        username: 'testuser'
                    });

                    expect($.cookie).toHaveBeenCalledWith('show_ew');
                    expect(session.get('diffsShowExtraWhitespace')).toBe(false);
                });
            });

            describe('Sets cookie', function() {
                beforeEach(function() {
                    spyOn($, 'cookie');
                });

                it('When true', function() {
                    session.attributes.diffsShowExtraWhitespace = false;
                    session.set('diffsShowExtraWhitespace', true);

                    expect($.cookie).toHaveBeenCalledWith('show_ew', 'true', {
                        path: SITE_ROOT
                    });
                });

                it('When false', function() {
                    session.attributes.diffsShowExtraWhitespace = true;
                    session.set('diffsShowExtraWhitespace', false);

                    expect($.cookie).toHaveBeenCalledWith('show_ew', 'false', {
                        path: SITE_ROOT
                    });
                });
            });
        });
    });
});
