describe('models/UserSession', function() {
    describe('create', function() {
        it('Instance is set', function() {
            var session = RB.UserSession.create({
                username: 'testuser'
            });

            expect(session).toBe(RB.UserSession.instance);
        });

        it('Second attempt fails', function() {
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
});
