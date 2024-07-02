import { suite } from '@beanbag/jasmine-suites';
import {
    beforeEach,
    describe,
    expect,
    it,
} from 'jasmine-core';

import { DefaultReviewer } from 'reviewboard/common';


suite('rb/resources/models/DefaultReviewer', function() {
    let model: DefaultReviewer;

    beforeEach(function() {
        model = new DefaultReviewer();
    });

    describe('parse', function() {
        it('API payloads', function() {
            const data = model.parse({
                default_reviewer: {
                    file_regex: '/foo/.*',
                    id: 42,
                    name: 'my-default-reviewer',
                },
                stat: 'ok',
            });

            expect(data).not.toBe(undefined);
            expect(data.id).toBe(42);
            expect(data.name).toBe('my-default-reviewer');
            expect(data.fileRegex).toBe('/foo/.*');
        });
    });

    describe('toJSON', function() {
        describe('name field', function() {
            it('With value', function() {
                model.set('name', 'foo');
                const data = model.toJSON();
                expect(data.name).toBe('foo');
            });
        });

        describe('fileRegex field', function() {
            it('With value', function() {
                model.set('fileRegex', '/foo/.*');
                const data = model.toJSON();
                expect(data.file_regex).toBe('/foo/.*');
            });
        });
    });
});
