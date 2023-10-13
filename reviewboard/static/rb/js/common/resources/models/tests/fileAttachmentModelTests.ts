import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import {
    BaseResource,
    FileAttachment,
} from 'reviewboard/common';


suite('rb/resources/models/FileAttachment', function() {
    let model;
    let parentObject;

    beforeEach(function() {
        parentObject = new BaseResource({
            public: true,
        });

        model = new FileAttachment({
            parentObject: parentObject,
        });
    });

    describe('toJSON', function() {
        describe('caption field', function() {
            it('With value', function() {
                model.set('caption', 'foo');
                const data = model.toJSON();
                expect(data.caption).toBe('foo');
            });
        });

        describe('file field', function() {
            it('With new file attachment', function() {
                expect(model.isNew()).toBe(true);

                model.set('file', 'abc');
                const data = model.toJSON();
                expect(data.path).toBe('abc');
            });

            it('With existing file attachment', function() {
                model.id = 123;
                model.attributes.id = 123;
                expect(model.isNew()).toBe(false);

                model.set('file', 'abc');
                const data = model.toJSON();
                expect(data.path).toBe(undefined);
            });
        });
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                stat: 'ok',
                file_attachment: {
                    attachment_history_id: 1,
                    caption: 'caption',
                    filename: 'filename',
                    id: 42,
                    review_url: 'reviewURL',
                    revision: 123,
                    state: 'Published',
                    thumbnail: 'thumbnailHTML',
                    url: 'downloadURL',
                },
            });

            expect(data).not.toBe(undefined);
            expect(data.attachmentHistoryID).toBe(1);
            expect(data.caption).toBe('caption');
            expect(data.downloadURL).toBe('downloadURL');
            expect(data.filename).toBe('filename');
            expect(data.id).toBe(42);
            expect(data.reviewURL).toBe('reviewURL');
            expect(data.revision).toBe(123);
            expect(data.state).toBe('Published');
            expect(data.thumbnailHTML).toBe('thumbnailHTML');
        });
    });
});
