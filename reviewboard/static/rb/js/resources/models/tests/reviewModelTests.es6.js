suite('rb/resources/models/Review', function() {
    let model;

    beforeEach(function() {
        model = new RB.Review({
            parentObject: new RB.ReviewRequest(),
        });
    });

    describe('createReply', function() {
        it('Returns cached draft reply', function() {
            expect(model.get('draftReply')).toBe(null);

            const reviewReply = model.createReply();
            expect(model.get('draftReply')).toBe(reviewReply);

            const reviewReply2 = model.createReply();
            expect(reviewReply).toBe(reviewReply2);
        });

        it('Cached draft reply resets on publish', function() {
            const reviewReply = model.createReply();
            expect(model.get('draftReply')).toBe(reviewReply);

            reviewReply.trigger('published');
            expect(model.get('draftReply')).toBe(null);
        });
    });

    describe('parse', function() {
        beforeEach(function() {
            model.rspNamespace = 'my_review';
        });

        it('Common API payloads', function() {
            const data = model.parse({
                stat: 'ok',
                my_review: {
                    id: 42,
                    body_top: 'my body top',
                    body_bottom: 'my body bottom',
                    'public': false,
                    body_top_text_type: 'markdown',
                    body_bottom_text_type: 'plain',
                    ship_it: false,
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.bodyTop).toBe('my body top');
            expect(data.bodyBottom).toBe('my body bottom');
            expect(data.public).toBe(false);
            expect(data.bodyTopRichText).toBe(true);
            expect(data.bodyBottomRichText).toBe(false);
            expect(data.shipIt).toBe(false);
        });

        it('With raw_text_fields', function() {
            const data = model.parse({
                stat: 'ok',
                my_review: {
                    body_top: 'my body top',
                    body_bottom: 'my body bottom',
                    body_top_text_type: 'markdown',
                    body_bottom_text_type: 'plain',
                    raw_text_fields: {
                        body_top: 'raw body top',
                        body_top_text_type: 'raw',
                        body_bottom: 'raw body bottom',
                        body_bottom_text_type: 'raw',
                    },
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.bodyTop).toBe('my body top');
            expect(data.bodyBottom).toBe('my body bottom');
            expect(data.bodyTopRichText).toBe(false);
            expect(data.bodyBottomRichText).toBe(false);

            expect(data.rawTextFields).toBeTruthy();
            expect(data.rawTextFields.bodyTop).toBe('raw body top');
            expect(data.rawTextFields.bodyBottom).toBe('raw body bottom');
        });

        it('With markdown_text_fields', function() {
            const data = model.parse({
                stat: 'ok',
                my_review: {
                    body_top: 'my body top',
                    body_bottom: 'my body bottom',
                    body_top_text_type: 'markdown',
                    body_bottom_text_type: 'plain',
                    markdown_text_fields: {
                        body_top: 'Markdown body top',
                        body_top_text_type: 'markdown',
                        body_bottom: 'Markdown body bottom',
                        body_bottom_text_type: 'markdown',
                    },
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.bodyTop).toBe('my body top');
            expect(data.bodyBottom).toBe('my body bottom');
            expect(data.bodyTopRichText).toBe(true);
            expect(data.bodyBottomRichText).toBe(false);

            expect(data.markdownTextFields).toBeTruthy();
            expect(data.markdownTextFields.bodyTop).toBe('Markdown body top');
            expect(data.markdownTextFields.bodyBottom)
                .toBe('Markdown body bottom');
        });

        it('With html_text_fields', function() {
            const data = model.parse({
                stat: 'ok',
                my_review: {
                    body_top: 'my body top',
                    body_bottom: 'my body bottom',
                    body_top_text_type: 'markdown',
                    body_bottom_text_type: 'plain',
                    html_text_fields: {
                        body_top: 'HTML body top',
                        body_top_text_type: 'html',
                        body_bottom: 'HTML body bottom',
                        body_bottom_text_type: 'html',
                    },
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.bodyTop).toBe('my body top');
            expect(data.bodyBottom).toBe('my body bottom');
            expect(data.bodyTopRichText).toBe(true);
            expect(data.bodyBottomRichText).toBe(false);

            expect(data.htmlTextFields).toBeTruthy();
            expect(data.htmlTextFields.bodyTop).toBe('HTML body top');
            expect(data.htmlTextFields.bodyBottom).toBe('HTML body bottom');
        });
    });

    describe('toJSON', function() {
        describe('bodyTop field', function() {
            it('With value', function() {
                model.set('bodyTop', 'foo');
                const data = model.toJSON();
                expect(data.body_top).toBe('foo');
            });
        });

        describe('bodyBottom field', function() {
            it('With value', function() {
                model.set('bodyBottom', 'foo');
                const data = model.toJSON();
                expect(data.body_bottom).toBe('foo');
            });
        });

        describe('force_text_type field', function() {
            it('With value', function() {
                model.set('forceTextType', 'html');
                const data = model.toJSON();
                expect(data.force_text_type).toBe('html');
            });

            it('Without value', function() {
                const data = model.toJSON();

                expect(data.force_text_type).toBe(undefined);
            });
        });

        describe('include_text_types field', function() {
            it('With value', function() {
                model.set('includeTextTypes', 'html');
                const data = model.toJSON();
                expect(data.include_text_types).toBe('html');
            });

            it('Without value', function() {
                const data = model.toJSON();

                expect(data.include_text_types).toBe(undefined);
            });
        });

        describe('public field', function() {
            it('With value', function() {
                model.set('public', true);
                const data = model.toJSON();
                expect(data.public).toBe(1);
            });

            it('Without value', function() {
                const data = model.toJSON();
                expect(data.public).toBe(undefined);
            });
        });

        describe('bodyTopRichText field', function() {
            it('With true', function() {
                model.set('bodyTopRichText', true);
                const data = model.toJSON();
                expect(data.body_top_text_type).toBe('markdown');
            });

            it('With false', function() {
                model.set('bodyTopRichText', false);
                const data = model.toJSON();
                expect(data.body_top_text_type).toBe('plain');
            });
        });

        describe('bodyBottomRichText field', function() {
            it('With true', function() {
                model.set('bodyBottomRichText', true);
                const data = model.toJSON();
                expect(data.body_bottom_text_type).toBe('markdown');
            });

            it('With false', function() {
                model.set('bodyBottomRichText', false);
                const data = model.toJSON();
                expect(data.body_bottom_text_type).toBe('plain');
            });
        });

        describe('shipIt field', function() {
            it('With value', function() {
                model.set('shipIt', true);
                const data = model.toJSON();
                expect(data.ship_it).toBe(true);
            });
        });
    });
});
