describe('resources/models/FileAttachmentComment', function() {
    var strings = RB.FileAttachmentComment.strings,
        model;

    beforeEach(function() {
        /* Set some sane defaults needed to pass validation. */
        model = new RB.FileAttachmentComment({
            fileAttachmentID: 16,
            parentObject: new RB.BaseResource({
                public: true
            })
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            var data = model.parse({
                stat: 'ok',
                file_attachment_comment: {
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    rich_text: true,
                    text: 'foo',
                    extra_data: {
                        my_int: 123,
                        my_bool: true,
                        my_str: 'strvalue',
                        my_null: null
                    },
                    link_text: 'my-link-text',
                    thumbnail_html: '<blink>Boo</blink>',
                    review_url: '/review-ui/',
                    file_attachment: {
                        id: 10,
                        filename: 'file.txt'
                    }
                }
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.issueOpened).toBe(true);
            expect(data.issueStatus).toBe(RB.BaseComment.STATE_RESOLVED);
            expect(data.richText).toBe(true);
            expect(data.text).toBe('foo');
            expect(data.extraData).not.toBe(undefined);
            expect(data.extraData.my_int).toBe(123);
            expect(data.extraData.my_bool).toBe(true);
            expect(data.extraData.my_str).toBe('strvalue');
            expect(data.extraData.my_null).toBe(null);
            expect(data.linkText).toBe('my-link-text');
            expect(data.thumbnailHTML).toBe('<blink>Boo</blink>');
            expect(data.reviewURL).toBe('/review-ui/');
            expect(data.fileAttachment).not.toBe(undefined);
            expect(data.fileAttachment.id).toBe(10);
            expect(data.fileAttachment.get('filename')).toBe('file.txt');
            expect(data.fileAttachmentID).toBe(10);
        });
    });

    describe('toJSON', function() {
        it('BaseComment.toJSON called', function() {
            spyOn(RB.BaseComment.prototype, 'toJSON').andCallThrough();
            model.toJSON();
            expect(RB.BaseComment.prototype.toJSON).toHaveBeenCalled();
        });

        it('extra_data field', function() {
            var data;

            model.set({
                extraData: {
                    my_int: 123,
                    my_bool: true,
                    my_str: 'strvalue',
                    my_null: null
                }
            });

            data = model.toJSON();
            expect(data['extra_data.my_int']).toBe(123);
            expect(data['extra_data.my_bool']).toBe(true);
            expect(data['extra_data.my_str']).toBe('strvalue');
            expect(data['extra_data.my_null']).toBe(null);
        });
    });

    describe('validate', function() {
        it('Inherited behavior', function() {
            spyOn(RB.BaseComment.prototype, 'validate');
            model.validate({});
            expect(RB.BaseComment.prototype.validate).toHaveBeenCalled();
        });

        describe('extraData', function() {
            describe('Valid values', function() {
                it('Empty object', function() {
                    expect(model.validate({
                        extraData: {}
                    })).toBe(undefined);
                });

                it('Populated object', function() {
                    expect(model.validate({
                        extraData: {
                            a: 42
                        }
                    })).toBe(undefined);
                });

                it('Undefined', function() {
                    expect(model.validate({
                        extraData: undefined
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                var errStr = strings.INVALID_EXTRADATA_TYPE;

                it('Array', function() {
                    expect(model.validate({
                        extraData: ''
                    })).toBe(errStr);
                });

                it('Boolean', function() {
                    expect(model.validate({
                        extraData: false
                    })).toBe(errStr);
                });

                it('Integer', function() {
                    expect(model.validate({
                        extraData: 0
                    })).toBe(errStr);
                });

                it('Null', function() {
                    expect(model.validate({
                        extraData: null
                    })).toBe(errStr);
                });

                it('String', function() {
                    expect(model.validate({
                        extraData: ''
                    })).toBe(errStr);
                });
            });
        });

        describe('extraData entries', function() {
            describe('Valid values', function() {
                it('Booleans', function() {
                    expect(model.validate({
                        extraData: {
                            value: true
                        }
                    })).toBe(undefined);
                });

                it('Integers', function() {
                    expect(model.validate({
                        extraData: {
                            value: 42
                        }
                    })).toBe(undefined);
                });

                it('Null', function() {
                    expect(model.validate({
                        extraData: {
                            value: null
                        }
                    })).toBe(undefined);
                });

                it('Strings', function() {
                    expect(model.validate({
                        extraData: {
                            value: 'foo'
                        }
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                var errStr = strings.INVALID_EXTRADATA_VALUE_TYPE
                    .replace('{key}', 'value');

                it('Arrays', function() {
                    expect(model.validate({
                        extraData: {
                            value: [1, 2, 3]
                        }
                    })).toBe(errStr);
                });

                it('NaN', function() {
                    expect(model.validate({
                        extraData: {
                            value: NaN
                        }
                    })).toBe(errStr);
                });

                it('Objects', function() {
                    expect(model.validate({
                        extraData: {
                            value: {
                                a: 1
                            }
                        }
                    })).toBe(errStr);
                });

                it('Undefined', function() {
                    expect(model.validate({
                        extraData: {
                            value: undefined
                        }
                    })).toBe(errStr);
                });
            });
        });
    });
});
