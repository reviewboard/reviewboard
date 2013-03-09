describe('models/ReviewReply', function() {
    var parentObject,
        model;

    beforeEach(function() {
        parentObject = new RB.BaseResource({
            public: true,
        });

        model = new RB.ReviewReply({
            parentObject: parentObject
        });
    });

    describe('parse', function() {
        beforeEach(function() {
            model.rspNamespace = 'my_reply';
        });

        it('API payloads', function() {
            var data = model.parse({
                my_reply: {
                    id: 42,
                    body_top: 'foo',
                    body_bottom: 'bar',
                    public: false
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.body_top).toBe('foo');
            expect(data.body_bottom).toBe('bar');
            expect(data.public).toBe(false);
        });
    });

    describe('toJSON', function() {
        describe('body_top field', function() {
            it('With value', function() {
                var data;

                model.set('body_top', 'foo');
                data = model.toJSON();
                expect(data.body_top).toBe('foo');
            });
        });

        describe('body_bottom field', function() {
            it('With value', function() {
                var data;

                model.set('body_bottom', 'foo');
                data = model.toJSON();
                expect(data.body_bottom).toBe('foo');
            });
        });

        describe('public field', function() {
            it('With value', function() {
                var data;

                model.set('public', true);
                data = model.toJSON();
                expect(data.public).toBe(true);
            });
        });
    });
});
