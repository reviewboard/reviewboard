suite('rb/resources/models/ScreenshotComment', function() {
    var strings = RB.ScreenshotComment.strings,
        model;

    beforeEach(function() {
        /* Set some sane defaults needed to pass validation. */
        model = new RB.ScreenshotComment({
            screenshotID: 16,
            parentObject: new RB.BaseResource({
                'public': true
            }),
            x: 0,
            y: 0,
            width: 1,
            height: 1
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                screenshot_comment: {
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    text_type: 'markdown',
                    text: 'foo',
                    x: 10,
                    y: 20,
                    w: 30,
                    h: 40,
                    thumbnail_url: '/thumbnail.png',
                    screenshot: {
                        id: 10,
                        filename: 'image.png'
                    }
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.issueOpened).toBe(true);
            expect(data.issueStatus).toBe(RB.BaseComment.STATE_RESOLVED);
            expect(data.richText).toBe(true);
            expect(data.text).toBe('foo');
            expect(data.x).toBe(10);
            expect(data.y).toBe(20);
            expect(data.width).toBe(30);
            expect(data.height).toBe(40);
            expect(data.thumbnailURL).toBe('/thumbnail.png');
            expect(data.screenshot).not.toBe(undefined);
            expect(data.screenshot.id).toBe(10);
            expect(data.screenshot.get('filename')).toBe('image.png');
            expect(data.screenshotID).toBe(10);
        });
    });

    describe('toJSON', function() {
        it('BaseComment.toJSON called', function() {
            spyOn(RB.BaseComment.prototype, 'toJSON').andCallThrough();
            model.toJSON();
            expect(RB.BaseComment.prototype.toJSON).toHaveBeenCalled();
        });

        it('x field', function() {
            var data;

            model.set('x', 10);

            data = model.toJSON();
            expect(data.x).toBe(10);
        });

        it('y field', function() {
            var data;

            model.set('y', 10);

            data = model.toJSON();
            expect(data.y).toBe(10);
        });

        it('w field', function() {
            var data;

            model.set('width', 10);

            data = model.toJSON();
            expect(data.w).toBe(10);
        });

        it('h field', function() {
            var data;

            model.set('height', 10);

            data = model.toJSON();
            expect(data.h).toBe(10);
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
    });

    describe('validate', function() {
        it('Inherited behavior', function() {
            spyOn(RB.BaseComment.prototype, 'validate');
            model.validate({});
            expect(RB.BaseComment.prototype.validate).toHaveBeenCalled();
        });

        describe('x', function() {
            describe('Valid values', function() {
                it('0', function() {
                    expect(model.validate({
                        x: 0
                    })).toBe(undefined);
                });

                it('> 0', function() {
                    expect(model.validate({
                        x: 10
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('< 0', function() {
                    expect(model.validate({
                        x: -1
                    })).toBe(strings.INVALID_X);
                });
            });
        });

        describe('y', function() {
            describe('Valid values', function() {
                it('0', function() {
                    expect(model.validate({
                        y: 0
                    })).toBe(undefined);
                });

                it('> 0', function() {
                    expect(model.validate({
                        y: 10
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('< 0', function() {
                    expect(model.validate({
                        y: -1
                    })).toBe(strings.INVALID_Y);
                });
            });
        });

        describe('width', function() {
            describe('Valid values', function() {
                it('> 0', function() {
                    expect(model.validate({
                        width: 10
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('0', function() {
                    expect(model.validate({
                        width: 0
                    })).toBe(strings.INVALID_WIDTH);
                });

                it('< 0', function() {
                    expect(model.validate({
                        width: -1
                    })).toBe(strings.INVALID_WIDTH);
                });
            });
        });

        describe('height', function() {
            describe('Valid values', function() {
                it('> 0', function() {
                    expect(model.validate({
                        height: 10
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('0', function() {
                    expect(model.validate({
                        height: 0
                    })).toBe(strings.INVALID_HEIGHT);
                });

                it('< 0', function() {
                    expect(model.validate({
                        height: -1
                    })).toBe(strings.INVALID_HEIGHT);
                });
            });
        });
    });
});
