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
    ScreenshotComment,
} from 'reviewboard/common';


suite('rb/resources/models/ScreenshotComment', function() {
    const strings = ScreenshotComment.strings;
    let model: ScreenshotComment;

    beforeEach(function() {
        /* Set some sane defaults needed to pass validation. */
        model = new ScreenshotComment({
            height: 1,
            parentObject: new BaseResource({
                'public': true,
            }),
            screenshotID: 16,
            width: 1,
            x: 0,
            y: 0,
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                screenshot_comment: {
                    h: 40,
                    id: 42,
                    issue_opened: true,
                    issue_status: 'resolved',
                    screenshot: {
                        filename: 'image.png',
                        id: 10,
                    },
                    text: 'foo',
                    text_type: 'markdown',
                    thumbnail_url: '/thumbnail.png',
                    w: 30,
                    x: 10,
                    y: 20,
                },
                stat: 'ok',
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.issueOpened).toBe(true);
            expect(data.issueStatus).toBe(BaseComment.STATE_RESOLVED);
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
            spyOn(BaseComment.prototype, 'toJSON').and.callThrough();
            model.toJSON();
            expect(BaseComment.prototype.toJSON).toHaveBeenCalled();
        });

        it('x field', function() {
            model.set('x', 10);
            const data = model.toJSON();
            expect(data.x).toBe(10);
        });

        it('y field', function() {
            model.set('y', 10);
            const data = model.toJSON();
            expect(data.y).toBe(10);
        });

        it('w field', function() {
            model.set('width', 10);
            const data = model.toJSON();
            expect(data.w).toBe(10);
        });

        it('h field', function() {
            model.set('height', 10);
            const data = model.toJSON();
            expect(data.h).toBe(10);
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
    });

    describe('validate', function() {
        it('Inherited behavior', function() {
            spyOn(BaseComment.prototype, 'validate');
            model.validate({});
            expect(BaseComment.prototype.validate).toHaveBeenCalled();
        });

        describe('x', function() {
            describe('Valid values', function() {
                it('0', function() {
                    expect(model.validate({
                        x: 0,
                    })).toBe(undefined);
                });

                it('> 0', function() {
                    expect(model.validate({
                        x: 10,
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('< 0', function() {
                    expect(model.validate({
                        x: -1,
                    })).toBe(strings.INVALID_X);
                });
            });
        });

        describe('y', function() {
            describe('Valid values', function() {
                it('0', function() {
                    expect(model.validate({
                        y: 0,
                    })).toBe(undefined);
                });

                it('> 0', function() {
                    expect(model.validate({
                        y: 10,
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('< 0', function() {
                    expect(model.validate({
                        y: -1,
                    })).toBe(strings.INVALID_Y);
                });
            });
        });

        describe('width', function() {
            describe('Valid values', function() {
                it('> 0', function() {
                    expect(model.validate({
                        width: 10,
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('0', function() {
                    expect(model.validate({
                        width: 0,
                    })).toBe(strings.INVALID_WIDTH);
                });

                it('< 0', function() {
                    expect(model.validate({
                        width: -1,
                    })).toBe(strings.INVALID_WIDTH);
                });
            });
        });

        describe('height', function() {
            describe('Valid values', function() {
                it('> 0', function() {
                    expect(model.validate({
                        height: 10,
                    })).toBe(undefined);
                });
            });

            describe('Invalid values', function() {
                it('0', function() {
                    expect(model.validate({
                        height: 0,
                    })).toBe(strings.INVALID_HEIGHT);
                });

                it('< 0', function() {
                    expect(model.validate({
                        height: -1,
                    })).toBe(strings.INVALID_HEIGHT);
                });
            });
        });
    });
});
