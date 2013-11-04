describe('resources/models/Review', function() {
    var model;

    beforeEach(function() {
        model = new RB.Review({
            parentObject: new RB.ReviewRequest()
        });
    });

    describe('createReply', function() {
        it('Returns cached draft reply', function() {
            var reviewReply,
                reviewReply2;

            expect(model.get('draftReply')).toBe(null);

            reviewReply = model.createReply();
            expect(model.get('draftReply')).toBe(reviewReply);

            reviewReply2 = model.createReply();
            expect(reviewReply).toBe(reviewReply2);
        });

        it('Cached draft reply resets on publish', function() {
            var reviewReply;

            reviewReply = model.createReply();
            expect(model.get('draftReply')).toBe(reviewReply);

            reviewReply.trigger('published');
            expect(model.get('draftReply')).toBe(null);
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
                    rich_text: true,
                    ship_it: false
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.bodyTop).toBe('foo');
            expect(data.bodyBottom).toBe('bar');
            expect(data.public).toBe(false);
            expect(data.richText).toBe(true);
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

        describe('richText field', function() {
            it('With value', function() {
                var data;

                model.set('richText', true);
                data = model.toJSON();
                expect(data.rich_text).toBe(true);
            });
        });

        describe('shipIt field', function() {
            it('With value', function() {
                var data;

                model.set('shipIt', true);
                data = model.toJSON();
                expect(data.ship_it).toBe(true);
            });
        });
    });
});
