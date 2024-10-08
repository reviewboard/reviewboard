import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import {
    BaseComment,
    BaseResource,
    FileAttachmentComment,
} from 'reviewboard/common';


suite('rb/resources/models/FileAttachmentComment', function() {
    const baseStrings = BaseResource.strings;
    let model: FileAttachmentComment;

    beforeEach(function() {
        /* Set some sane defaults needed to pass validation. */
        model = new FileAttachmentComment({
            fileAttachmentID: 16,
            parentObject: new BaseResource({
                'public': true,
            }),
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                file_attachment_comment: {
                    extra_data: {
                        my_bool: true,
                        my_int: 123,
                        my_null: null,
                        my_str: 'strvalue',
                    },
                    file_attachment: {
                        filename: 'file.txt',
                        id: 10,
                    },
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    link_text: 'my-link-text',
                    review_url: '/review-ui/',
                    text: 'foo',
                    text_type: 'markdown',
                    thumbnail_html: '<blink>Boo</blink>',
                },
                stat: 'ok',
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.issueOpened).toBe(true);
            expect(data.issueStatus).toBe(BaseComment.STATE_RESOLVED);
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
            spyOn(BaseComment.prototype, 'toJSON').and.callThrough();
            model.toJSON();
            expect(BaseComment.prototype.toJSON).toHaveBeenCalled();
        });

        describe('diff_against_file_attachment_id field', function() {
            it('When loaded', function() {
                model.set({
                    diffAgainstFileAttachmentID: 123,
                    loaded: true,
                });
                const data = model.toJSON();
                expect(data.diff_against_file_attachment_id).toBe(undefined);
            });

            describe('When not loaded', function() {
                it('With value', function() {
                    model.set('diffAgainstFileAttachmentID', 123);
                    const data = model.toJSON();
                    expect(data.diff_against_file_attachment_id).toBe(123);
                });

                it('Without value', function() {
                    const data = model.toJSON();
                    expect(data.diff_against_file_attachment_id)
                        .toBe(undefined);
                });
            });
        });

        describe('file_attachment_id field', function() {
            it('When loaded', function() {
                model.set({
                    fileAttachmentID: 123,
                    loaded: true,
                });

                const data = model.toJSON();
                expect(data.file_attachment_id).toBe(undefined);
            });

            it('When not loaded', function() {
                model.set('fileAttachmentID', 123);
                const data = model.toJSON();
                expect(data.file_attachment_id).toBe(123);
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

        it('extra_data field', function() {
            model.set({
                extraData: {
                    my_bool: true,
                    my_int: 123,
                    my_null: null,
                    my_str: 'strvalue',
                },
            });

            const data = model.toJSON();
            expect(data['extra_data.my_int']).toBe(123);
            expect(data['extra_data.my_bool']).toBe(true);
            expect(data['extra_data.my_str']).toBe('strvalue');
            expect(data['extra_data.my_null']).toBe(null);
        });
    });

    describe('validate', function() {
        it('Inherited behavior', function() {
            spyOn(BaseComment.prototype, 'validate');
            model.validate({});
            expect(BaseComment.prototype.validate).toHaveBeenCalled();
        });

        describe('extraData', function() {
            describe('Valid values', function() {
                it('Empty object', function() {
                    expect(model.validate({
                        extraData: {},
                    })).toBe(undefined);
                });

                it('Populated object', function() {
                    expect(model.validate({
                        extraData: {
                            a: 42,
                        },
                    })).toBe(undefined);
                });

                it('Undefined', function() {
                    expect(model.validate({
                        extraData: undefined,
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                const errStr = baseStrings.INVALID_EXTRADATA_TYPE;

                it('Array', function() {
                    expect(model.validate({
                        extraData: '',
                    })).toBe(errStr);
                });

                it('Boolean', function() {
                    expect(model.validate({
                        extraData: false,
                    })).toBe(errStr);
                });

                it('Integer', function() {
                    expect(model.validate({
                        extraData: 0,
                    })).toBe(errStr);
                });

                it('Null', function() {
                    expect(model.validate({
                        extraData: null,
                    })).toBe(errStr);
                });

                it('String', function() {
                    expect(model.validate({
                        extraData: '',
                    })).toBe(errStr);
                });
            });
        });

        describe('extraData entries', function() {
            describe('Valid values', function() {
                it('Booleans', function() {
                    expect(model.validate({
                        extraData: {
                            value: true,
                        },
                    })).toBe(undefined);
                });

                it('Integers', function() {
                    expect(model.validate({
                        extraData: {
                            value: 42,
                        },
                    })).toBe(undefined);
                });

                it('Null', function() {
                    expect(model.validate({
                        extraData: {
                            value: null,
                        },
                    })).toBe(undefined);
                });

                it('Strings', function() {
                    expect(model.validate({
                        extraData: {
                            value: 'foo',
                        },
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                const errStr = baseStrings.INVALID_EXTRADATA_VALUE_TYPE
                    .replace('{key}', 'value');

                it('Arrays', function() {
                    expect(model.validate({
                        extraData: {
                            value: [1, 2, 3],
                        },
                    })).toBe(errStr);
                });

                it('NaN', function() {
                    expect(model.validate({
                        extraData: {
                            value: NaN,
                        },
                    })).toBe(errStr);
                });

                it('Objects', function() {
                    expect(model.validate({
                        extraData: {
                            value: {
                                a: 1,
                            },
                        },
                    })).toBe(errStr);
                });

                it('Undefined', function() {
                    expect(model.validate({
                        extraData: {
                            value: undefined,
                        },
                    })).toBe(errStr);
                });
            });
        });
    });
});
