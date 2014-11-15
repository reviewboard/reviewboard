suite('rb/resources/models/Review', function() {
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
                    'public': false,
                    body_top_text_type: 'markdown',
                    body_bottom_text_type: 'plain',
                    ship_it: false
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.bodyTop).toBe('foo');
            expect(data.bodyBottom).toBe('bar');
            expect(data['public']).toBe(false);
            expect(data.bodyTopRichText).toBe(true);
            expect(data.bodyBottomRichText).toBe(false);
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

        describe('force_text_type field', function() {
            it('With value', function() {
                var data;

                model.set('forceTextType', 'html');
                data = model.toJSON();
                expect(data.force_text_type).toBe('html');
            });

            it('Without value', function() {
                var data = model.toJSON();

                expect(data.force_text_type).toBe(undefined);
            });
        });

        describe('include_text_types field', function() {
            it('With value', function() {
                var data;

                model.set('includeTextTypes', 'html');
                data = model.toJSON();
                expect(data.include_text_types).toBe('html');
            });

            it('Without value', function() {
                var data = model.toJSON();

                expect(data.include_text_types).toBe(undefined);
            });
        });

        describe('public field', function() {
            it('With value', function() {
                var data;

                model.set('public', true);
                data = model.toJSON();
                expect(data['public']).toBe(1);
            });

            it('Without value', function() {
                var data = model.toJSON();
                expect(data['public']).toBe(undefined);
            });
        });

        describe('bodyTopRichText field', function() {
            it('With true', function() {
                var data;

                model.set('bodyTopRichText', true);
                data = model.toJSON();
                expect(data.body_top_text_type).toBe('markdown');
            });

            it('With false', function() {
                var data;

                model.set('bodyTopRichText', false);
                data = model.toJSON();
                expect(data.body_top_text_type).toBe('plain');
            });
        });

        describe('bodyBottomRichText field', function() {
            it('With true', function() {
                var data;

                model.set('bodyBottomRichText', true);
                data = model.toJSON();
                expect(data.body_bottom_text_type).toBe('markdown');
            });

            it('With false', function() {
                var data;

                model.set('bodyBottomRichText', false);
                data = model.toJSON();
                expect(data.body_bottom_text_type).toBe('plain');
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
