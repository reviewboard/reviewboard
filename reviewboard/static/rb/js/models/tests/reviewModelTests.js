describe('models/Review', function() {
    var parentObject,
        model;

    beforeEach(function() {
        model = new RB.Review({
            parentObject: new RB.BaseResource()
        });
    });

    describe('parse', function() {
        beforeEach(function() {
            model.rspNamespace = 'my_review';
        });

        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                my_review: {
                    id: 42,
                    body_top: 'foo',
                    body_bottom: 'bar',
                    public: false,
                    ship_it: false
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.bodyTop).toBe('foo');
            expect(data.bodyBottom).toBe('bar');
            expect(data.public).toBe(false);
            expect(data.shipIt).toBe(false);
        });
    });

    describe('toJSON', function() {
        describe('bodyTop field', function() {
            it('With value', function() {
                var data;

                model.set('bodyTop', 'foo');
                data = model.toJSON();
                expect(data.body_top).toBe('foo');
            });
        });

        describe('bodyBottom field', function() {
            it('With value', function() {
                var data;

                model.set('bodyBottom', 'foo');
                data = model.toJSON();
                expect(data.body_bottom).toBe('foo');
            });
        });

        describe('public field', function() {
            it('With value', function() {
                var data;

                model.set('public', true);
                data = model.toJSON();
                expect(data.public).toBe(1);
            });

            it('Without value', function() {
                var data = model.toJSON();
                expect(data.public).toBe(undefined);
            });
        });

        describe('shipIt field', function() {
            it('With value', function() {
                var data;

                model.set('shipIt', true);
                data = model.toJSON();
                expect(data.ship_it).toBe(1);
            });
        });
    });
});
